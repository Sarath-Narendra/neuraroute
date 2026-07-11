"""Standalone NeuraRoute device agent.

Run it like this:
    python runtime/agent.py configs/pc.yaml

The agent connects to an MQTT broker, publishes heartbeats, listens for tasks on
neuraroute/task/<device_id>, listens for admin commands on neuraroute/admin,
executes tasks, and publishes results.
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

try:
    from runtime.telemetry import get_telemetry, simulate_battery_critical, clear_override
except ImportError:
    # TODO: import real telemetry.py once teammate/you finish it
    def get_telemetry(device_type: str, telemetry_mode: str, device_id: str | None = None) -> dict[str, Any]:
        return {"battery": 100.0, "cpu_load": 0.0, "npu_load": None}

    def simulate_battery_critical(device_id: str) -> None:
        pass

    def clear_override(device_id: str) -> None:
        pass

try:
    from models.run_model import run_model
except ImportError:
    def run_model(op: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "mock",
            "op": op,
            "note": "run_model not available yet — dummy result",
        }


LOGGER = logging.getLogger("neuraroute.agent")


class DeviceAgent:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.device_id = str(self.config.get("device_id", "unknown-device"))
        self.device_type = str(self.config.get("device_type", "pc"))
        self.accelerators = list(self.config.get("accelerators", []))
        self.supported_ops = list(self.config.get("supported_ops", []))
        self.telemetry_mode = str(self.config.get("telemetry_mode", "simulated"))

        self.broker_host, self.broker_port = self._parse_broker_env()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.device_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.shutdown_event = threading.Event()
        self.heartbeat_thread: threading.Thread | None = None
        self.connected = False

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a YAML mapping")
        return data

    def _parse_broker_env(self) -> tuple[str, int]:
        broker_value = os.environ.get("NEURAROUTE_BROKER", "localhost:1883")
        if ":" not in broker_value:
            raise ValueError("NEURAROUTE_BROKER must be in format host:port")
        host, port_text = broker_value.rsplit(":", 1)
        return host, int(port_text)

    def start(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        LOGGER.info("Starting device agent for %s", self.device_id)
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

        try:
            self._publish_offline_heartbeat()
        except Exception as exc:  # pragma: no cover - best effort shutdown
            LOGGER.warning("Failed to publish offline heartbeat: %s", exc)

        if self.client.is_connected():
            self.client.disconnect()
        self.client.loop_stop()
        LOGGER.info("Agent stopped for %s", self.device_id)

    def _heartbeat_loop(self) -> None:
        while not self.shutdown_event.is_set():
            if self.client.is_connected():
                telemetry = get_telemetry(self.device_type, self.telemetry_mode, self.device_id)

                # Standardize battery on the wire as a 0.0-1.0 fraction (matches
                # contracts/heartbeat.schema.json's expected shape), even though
                # telemetry.py internally works in 0-100 (psutil/Termux native units).
                raw_battery = telemetry.get("battery")
                battery_fraction = None if raw_battery is None else round(raw_battery / 100.0, 4)

                payload = {
                    "device_id": self.device_id,
                    "timestamp": time.time(),
                    "battery": battery_fraction,
                    "cpu_load": telemetry.get("cpu_load"),
                    "npu_load": telemetry.get("npu_load"),
                    "status": "alive",
                    "accelerators": self.accelerators,
                }
                # TODO: replace with contracts/heartbeat.schema.json once frozen
                self.client.publish("neuraroute/heartbeat", json.dumps(payload), qos=1, retain=False)
                LOGGER.info("Published heartbeat for %s", self.device_id)
            self.shutdown_event.wait(1.5)

    def _publish_offline_heartbeat(self) -> None:
        payload = {
            "device_id": self.device_id,
            "timestamp": time.time(),
            "battery": None,
            "cpu_load": None,
            "npu_load": None,
            "status": "offline",
            "accelerators": self.accelerators,
        }
        self.client.publish("neuraroute/heartbeat", json.dumps(payload), qos=1, retain=False)
        LOGGER.info("Published offline heartbeat for %s", self.device_id)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        if reason_code == 0:
            self.connected = True
            task_topic = f"neuraroute/task/{self.device_id}"
            client.subscribe(task_topic, qos=1)
            client.subscribe("neuraroute/admin", qos=1)
            LOGGER.info(
                "Connected to broker %s:%s; subscribed to %s and neuraroute/admin",
                self.broker_host, self.broker_port, task_topic,
            )
        else:
            LOGGER.warning("MQTT connect failed with code %s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any = None) -> None:
        self.connected = False
        if not self.shutdown_event.is_set():
            LOGGER.warning("Disconnected from broker; reconnecting with backoff")

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        if message.topic == "neuraroute/admin":
            self._handle_admin_message(message)
            return
        self._handle_task_message(client, message)

    def _handle_admin_message(self, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Received invalid JSON admin payload: %s", exc)
            return

        target_device_id = payload.get("device_id")
        if target_device_id not in (None, self.device_id):
            return  # this admin message was meant for a different device

        command = payload.get("command")
        if command == "simulate_battery_critical":
            simulate_battery_critical(self.device_id)
            LOGGER.info("Admin: forcing next battery reading to critical for %s", self.device_id)
        elif command == "clear_override":
            clear_override(self.device_id)
            LOGGER.info("Admin: cleared battery override for %s", self.device_id)
        else:
            LOGGER.warning("Unknown admin command: %s", command)

    def _handle_task_message(self, client: mqtt.Client, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Received invalid JSON task payload: %s", exc)
            return

        task_id = payload.get("task_id")
        target_device_id = payload.get("device_id")
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
            else:
                result = run_model(op, task_payload)

            if not isinstance(result, dict):
                result = {"value": result}

            status = "success"
            error = None
        except Exception as exc:  # pragma: no cover - defensive path
            status = "error"
            result = None
            error = str(exc)
            LOGGER.exception("Task %s failed", task_id)

        duration_ms = (time.time() - start_time) * 1000.0
        response_payload = {
            "task_id": task_id,
            "device_id": self.device_id,
            "status": status,
            "result": result,
            "error": error,
            "duration_ms": duration_ms,
        }
        # TODO: replace with contracts/result.schema.json once frozen
        topic = f"neuraroute/result/{task_id}"
        client.publish(topic, json.dumps(response_payload), qos=1, retain=False)
        LOGGER.info("Published result for task %s on %s", task_id, topic)

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