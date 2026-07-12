"""Standalone NeuraRoute device agent (v2 — vitals triage tiers).

Run it like this:
    python runtime/agent.py runtime/configs/pc.yaml

The agent connects to the MQTT broker, publishes liveness heartbeats, listens for
triage tasks on neuraroute/task/<device_id>, executes them via models.run_model, and
publishes results.

The arduino agent additionally runs the ALWAYS-ON WATCHDOG (config `watchdog: true`):
it subscribes to every raw reading on neuraroute/reading and, independent of whatever
tier the engine picked, runs the hard tripwire + the local SLM on it. An extreme
emergency publishes an sos alert to neuraroute/sos (-> doctor's phone) and prints the
verdict to the serial bridge (-> Arduino IDE serial monitor / LED).
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit("paho-mqtt>=2.0 is required: pip install \"paho-mqtt>=2.0\"") from exc

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

from contracts.topics import (
    EV_SOS, HEARTBEAT_INTERVAL_S, SEV_EMERGENCY, TOPIC_ADMIN, TOPIC_HEARTBEAT,
    TOPIC_READING, TOPIC_SOS, broker_host, topic_result, topic_task,
)

try:
    # run_model is exported from the models package __init__, not a submodule.
    from models import run_model
    from models.tripwire import tripwire
except ImportError:
    def run_model(op: str, payload: dict[str, Any], device: str = "unknown") -> dict[str, Any]:
        return {
            "status": "mock",
            "op": op,
            "note": "run_model not available yet — dummy result",
        }

    def tripwire(vitals: dict) -> tuple[str, list[str]]:
        return "normal", []


LOGGER = logging.getLogger("neuraroute.agent")

SOS_COOLDOWN_S = 45.0   # per-patient: don't re-alert the doctor every 20 s for the same crisis


def adapt_task_payload(op: str, task_payload: dict[str, Any]) -> dict[str, Any]:
    """v2: the engine already sends run_model's flat shape {patient_id, vitals, profile}."""
    return dict(task_payload)


class DeviceAgent:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.device_id = str(self.config.get("device_id", "unknown-device"))
        self.device_type = str(self.config.get("device_type", "pc"))
        self.supported_ops = list(self.config.get("supported_ops", []))
        self.privacy_ok = bool(self.config.get("privacy_ok", True))

        # --- watchdog (arduino): always-on safety path -------------------------------
        self.watchdog = bool(self.config.get("watchdog", False))
        self.records = self._load_records(self.config.get("records_path"))
        self.serial_port = self.config.get("serial_port")
        self._serial = None
        self._last_sos: dict[str, float] = {}

        self.broker_host, self.broker_port = self._parse_broker_env()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.device_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.shutdown_event = threading.Event()
        self.heartbeat_thread: threading.Thread | None = None
        self.connected = False
        self._pid_file: Path | None = None

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a YAML mapping")
        return data

    def _load_records(self, records_path: str | None) -> dict[str, dict]:
        """The device's LOCAL copy of the patient records (the arduino's 'on-chip' story)."""
        path = Path(records_path) if records_path else Path(ROOT_DIR) / "data" / "patients.json"
        try:
            with path.open("r", encoding="utf-8") as handle:
                return {p["patient_id"]: p for p in json.load(handle)}
        except Exception:
            if self.config.get("watchdog"):
                LOGGER.warning("watchdog has no local records (%s) — triaging without history", path)
            return {}

    def _parse_broker_env(self) -> tuple[str, int]:
        # host-only (default port 1883) to match engine/dev_up/runbooks; host:port also accepted
        broker_value = os.environ.get("NEURAROUTE_BROKER", "localhost")
        if ":" in broker_value:
            host, port_text = broker_value.rsplit(":", 1)
            return host, int(port_text)
        return broker_value, 1883

    def start(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        LOGGER.info("Starting device agent for %s (watchdog=%s)", self.device_id, self.watchdog)
        self._write_pidfile()
        self._open_serial()
        self.client.connect_async(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        try:
            while not self.shutdown_event.is_set():
                time.sleep(0.2)
        except KeyboardInterrupt:
            self.shutdown_event.set()
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self.shutdown_event.is_set():
            return
        self.shutdown_event.set()
        if self.client.is_connected():
            self.client.disconnect()
        self.client.loop_stop()
        self._remove_pidfile()
        LOGGER.info("Agent stopped for %s", self.device_id)

    def _write_pidfile(self) -> None:
        """Record THIS python process's PID so kill_device.sh / dev_down.sh hit the real agent.

        On Git Bash for Windows `exec` does NOT replace the launcher shell (there is no
        image-replacing execve for a native .exe), so the PID dev_up.sh captured via `$!` is
        the bash WRAPPER, not this python. Killing that wrapper orphans us — we keep
        heartbeating and the tier never goes stale. Overwriting the pidfile with our own PID
        makes a kill actually land on the process that heartbeats.
        """
        try:
            self._pid_file = Path(ROOT_DIR) / "run" / "pids" / f"{self.device_id}.pid"
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file.write_text(str(os.getpid()), encoding="utf-8")
        except Exception as exc:  # best-effort — never block startup on bookkeeping
            LOGGER.debug("could not write pidfile: %s", exc)
            self._pid_file = None

    def _remove_pidfile(self) -> None:
        if self._pid_file is not None:
            try:
                self._pid_file.unlink(missing_ok=True)
            except Exception:
                pass

    # --- heartbeat: liveness only (the ladder routes on reachability, not load) ------
    def _heartbeat_loop(self) -> None:
        while not self.shutdown_event.is_set():
            if self.client.is_connected():
                payload = {
                    "device_id": self.device_id,
                    "ts": time.time(),
                    "models": self.supported_ops,   # ops this tier can run — feasibility needs this
                    "privacy_ok": self.privacy_ok,
                }
                self.client.publish(TOPIC_HEARTBEAT, json.dumps(payload), qos=1, retain=False)
            self.shutdown_event.wait(HEARTBEAT_INTERVAL_S)

    # --- mqtt ------------------------------------------------------------------------
    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if reason_code == 0:
            self.connected = True
            task_topic = topic_task(self.device_id)
            client.subscribe(task_topic, qos=1)
            client.subscribe(TOPIC_ADMIN, qos=1)
            if self.watchdog:
                client.subscribe(TOPIC_READING, qos=1)
                LOGGER.info("watchdog armed: analyzing every reading on %s", TOPIC_READING)
            LOGGER.info("Connected to broker %s:%s; subscribed to %s",
                        self.broker_host, self.broker_port, task_topic)
        else:
            LOGGER.warning("MQTT connect failed with code %s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any = None) -> None:
        self.connected = False
        if not self.shutdown_event.is_set():
            LOGGER.warning("Disconnected from broker; reconnecting with backoff")

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        if message.topic == TOPIC_ADMIN:
            self._handle_admin_message(message)
        elif message.topic == TOPIC_READING:
            threading.Thread(target=self._handle_reading, args=(message,), daemon=True).start()
        else:
            # Offload triage to a worker thread (like the reading path above). run_model can
            # block for seconds on a real /infer (the phone SLM esp.), and this callback runs
            # on paho's single network thread — blocking it starves outgoing heartbeats, so the
            # engine's 3 s stale monitor falsely marks the tier dropped mid-task and fails the
            # reading over before the (valid) verdict lands. A worker keeps heartbeats flowing.
            threading.Thread(target=self._handle_task_message, args=(client, message), daemon=True).start()

    def _handle_admin_message(self, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Received invalid JSON admin payload: %s", exc)
            return
        target_device_id = payload.get("device_id")
        if target_device_id not in (None, self.device_id):
            return
        LOGGER.info("Admin command %r acknowledged (v2 agents have no telemetry to override)",
                    payload.get("command"))

    # --- the quality path: engine-dispatched triage tasks -----------------------------
    def _handle_task_message(self, client: mqtt.Client, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Received invalid JSON task payload: %s", exc)
            return

        task_id = payload.get("task_id")
        target_device_id = payload.get("assigned_device")   # contract field is assigned_device
        if target_device_id not in (None, self.device_id):
            return

        start_time = time.time()
        try:
            op = payload.get("op", "")
            task_payload = payload.get("payload") or {}
            if not isinstance(task_payload, dict):
                raise ValueError("task payload must be a JSON object")

            if op == "echo":
                result = {"echo": task_payload}
                status = "ok"      # result.schema.json status enum: ok | error | timeout
                error = None
            else:
                adapted = adapt_task_payload(op, task_payload)
                result = run_model(op, adapted, device=self.device_id)
                # run_model returns an envelope; surface its status on the wire so a
                # failed op (GPT unreachable, LLM down) fails over DOWN THE LADDER
                # instead of masquerading as ok.
                if isinstance(result, dict) and result.get("status") in ("error", "timeout"):
                    status = result["status"]
                    error = result.get("error")
                else:
                    status = "ok"
                    error = None

            if not isinstance(result, dict):
                result = {"value": result}

        except Exception as exc:  # pragma: no cover - defensive path
            status = "error"
            result = None
            error = str(exc)
            LOGGER.exception("Task %s failed", task_id)

        finished = time.time()
        inner = (result or {}).get("result") if isinstance(result, dict) else None
        response_payload = {
            "task_id": task_id,
            "request_id": payload.get("request_id"),   # REQUIRED — engine matches results by this
            "device_id": self.device_id,
            "op": op,
            "status": status,
            "result": inner if isinstance(inner, dict) else result,
            "started_ts": start_time,
            "finished_ts": finished,
            "latency_ms": round((finished - start_time) * 1000.0, 1),
            "error": error,
        }
        client.publish(topic_result(task_id), json.dumps(response_payload), qos=1, retain=False)
        LOGGER.info("Published result for task %s (%s)", task_id, status)
        # the tier that ran the triage also narrates it on the serial bridge
        if status == "ok" and isinstance(inner, dict) and inner.get("severity"):
            self._serial_write(f"[{inner.get('patient_id', '?')}] {inner['severity'].upper()}"
                               f" (triage on {self.device_id}): {inner.get('transcript', '')}")

    # --- the safety path: the always-on watchdog --------------------------------------
    def _handle_reading(self, message: mqtt.MQTTMessage) -> None:
        try:
            reading = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        patient_id = str(reading.get("patient_id", "unknown"))
        vitals = reading.get("vitals") or {}

        # 1) hard tripwire first — instant, deterministic, cannot hallucinate
        severity, reasons = tripwire(vitals)
        if severity == SEV_EMERGENCY:
            self._raise_sos(patient_id, vitals, "tripwire: " + "; ".join(reasons))

        # 2) SLM pass on the SAME reading — catches what fixed bounds can't, and
        #    writes the detailed note to the serial monitor
        profile = self.records.get(patient_id, {})
        out = run_model("triage", {"patient_id": patient_id, "vitals": vitals,
                                   "profile": profile}, device=self.device_id)
        if isinstance(out, dict) and out.get("status") == "ok":
            verdict = out.get("result") or {}
            slm_sev = verdict.get("severity")
            if severity != SEV_EMERGENCY and slm_sev == SEV_EMERGENCY:
                self._raise_sos(patient_id, vitals,
                                "SLM: " + (verdict.get("transcript") or "")[:200])
            self._serial_write(f"[{patient_id}] {str(slm_sev or '?').upper()} (watchdog):"
                               f" {verdict.get('transcript', '')}")
        elif severity == SEV_EMERGENCY:
            self._serial_write(f"[{patient_id}] EMERGENCY (tripwire): {'; '.join(reasons)}")

    def _raise_sos(self, patient_id: str, vitals: dict, reason: str) -> None:
        now = time.time()
        if now - self._last_sos.get(patient_id, 0.0) < SOS_COOLDOWN_S:
            LOGGER.info("sos for %s suppressed (cooldown)", patient_id)
            return
        self._last_sos[patient_id] = now
        alert = {"type": EV_SOS, "ts": now, "patient_id": patient_id,
                 "severity": SEV_EMERGENCY, "reason": reason, "vitals": vitals,
                 "source": f"watchdog-{self.device_id}", "device_id": self.device_id}
        self.client.publish(TOPIC_SOS, json.dumps(alert), qos=1, retain=False)
        LOGGER.warning("SOS RAISED for %s: %s", patient_id, reason)
        self._serial_write(f"!!! EMERGENCY {patient_id}: {reason}")

    # --- serial bridge -> STM32 -> Arduino IDE serial monitor + LED -------------------
    def _open_serial(self) -> None:
        if not self.serial_port:
            return
        try:
            import serial  # pyserial, optional
            self._serial = serial.Serial(self.serial_port, 115200, timeout=1)
            LOGGER.info("serial bridge open on %s", self.serial_port)
        except Exception as exc:
            LOGGER.warning("serial bridge unavailable (%s) — mirroring to log only", exc)

    def _serial_write(self, line: str) -> None:
        line = " ".join(str(line).split())    # single line, no embedded newlines
        if self._serial is not None:
            try:
                self._serial.write((line + "\n").encode("utf-8", "replace"))
            except Exception as exc:
                LOGGER.warning("serial write failed: %s", exc)
        LOGGER.info("[SERIAL] %s", line)

    def _handle_signal(self, signum: int, _frame: Any) -> None:
        LOGGER.info("Received signal %s; shutting down", signum)
        self.shutdown_event.set()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python runtime/agent.py <path-to-config.yaml>")

    config_path = Path(sys.argv[1]).expanduser()
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()

    agent = DeviceAgent(config_path)
    agent.start()


if __name__ == "__main__":
    main()
