#!/usr/bin/env python3
"""runtime/agent.py — universal NeuraRoute device agent  (v0 SKELETON — owner: Gowtham).

The same ~150-line agent runs on every node: the Surface PC, the OnePlus (Termux), and the
Arduino Uno Q (Debian). It reads a device config, heartbeats its telemetry, executes any task
dispatched to it (via models.run_model when Eswar's ops land), and publishes the result.
Point it at the broker with NEURAROUTE_BROKER:

    NEURAROUTE_BROKER=192.168.1.5 python runtime/agent.py runtime/configs/phone-01.yaml

Built against the frozen contracts, so it already round-trips today. Gowtham owns runtime/ and
hardens the two spots marked TODO(Gowtham):
  1. real per-platform telemetry (Termux battery is wired; add psutil for laptops, temp/RAM)
  2. wiring real ops — happens automatically once models/run_model exists; echo/stub until then.
"""
import json
import os
import random
import signal
import subprocess
import sys
import threading
import time

# run directly as `python runtime/agent.py ...` from the repo root -> put repo root on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402
import paho.mqtt.client as mqtt  # noqa: E402

from contracts.topics import (  # noqa: E402
    BROKER_PORT, HEARTBEAT_INTERVAL_S, RESULT_ERROR, RESULT_OK, TOPIC_ADMIN,
    TOPIC_HEARTBEAT, broker_host, topic_result, topic_task,
)

# Real ops (Eswar). Absent until models/ lands -> we stub, so the plumbing works regardless.
try:
    from models import run_model  # run_model(op, payload) -> result
except Exception:
    run_model = None


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("accelerators", ["cpu"])
    cfg.setdefault("models", ["echo"])
    cfg.setdefault("privacy_ok", True)
    cfg.setdefault("telemetry_mode", "simulated")
    return cfg


def read_real_battery():
    """Best-effort real battery. Termux (Android) is wired; TODO(Gowtham): psutil for laptops."""
    try:
        out = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=3)
        if out.returncode == 0:
            d = json.loads(out.stdout)
            return {"percent": float(d["percentage"]),
                    "charging": str(d.get("status", "")).upper() == "CHARGING"}
    except Exception:
        pass
    return None  # mains-powered / telemetry unavailable


class Agent:
    def __init__(self, cfg):
        self.cfg = cfg
        self.device_id = cfg["device_id"]
        self.mode = cfg["telemetry_mode"]
        self._running = True
        self._batt_override = None          # sticky battery from simulate_battery_critical
        self._sim_batt = 78.0
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"agent-{self.device_id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self):
        self.client.reconnect_delay_set(min_delay=1, max_delay=5)
        self.client.connect_async(broker_host(), BROKER_PORT, keepalive=15)
        self.client.loop_start()
        threading.Thread(target=self._hb_loop, daemon=True).start()
        print(f"[{self.device_id}] up — heartbeating (mode={self.mode}, models={self.cfg['models']})",
              flush=True)

    def stop(self):
        self._running = False
        try:
            self.client.loop_stop(); self.client.disconnect()
        except Exception:
            pass

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        client.subscribe(topic_task(self.device_id))
        client.subscribe(TOPIC_ADMIN)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
        except Exception:
            return
        if msg.topic == TOPIC_ADMIN:
            self._admin(data)
        else:
            threading.Thread(target=self._run_task, args=(data,), daemon=True).start()

    def _admin(self, d):
        if d.get("device_id") not in (None, self.device_id):
            return
        if d.get("cmd") == "simulate_battery_critical":
            self._batt_override = {"percent": 4.0, "charging": False}
            print(f"[{self.device_id}] !! battery critical (4%)", flush=True)
        elif d.get("cmd") == "reset":
            self._batt_override = None
            self._sim_batt = 78.0

    def _battery(self):
        if self._batt_override:
            return self._batt_override
        if self.mode == "real":
            return read_real_battery()
        self._sim_batt = max(1.0, self._sim_batt - 0.1)   # simulated slow discharge
        return {"percent": round(self._sim_batt, 1), "charging": False}

    def _hb_loop(self):
        while self._running:
            # TODO(Gowtham): real cpu/npu/temp/ram via psutil in 'real' mode; placeholders for now.
            hb = {
                "device_id": self.device_id, "ts": time.time(),
                "accelerators": self.cfg["accelerators"], "models": self.cfg["models"],
                "battery": self._battery(),
                "cpu_load": round(random.uniform(0.1, 0.4), 3),
                "npu_load": round(random.uniform(0.05, 0.3), 3),
                "temperature_c": round(random.uniform(40, 50), 1),
                "ram_free_mb": random.randint(2000, 20000),
                "net": {"reachable": True, "latency_ms": 15},
                "privacy_ok": self.cfg["privacy_ok"], "telemetry_mode": self.mode,
            }
            self.client.publish(TOPIC_HEARTBEAT, json.dumps(hb))
            time.sleep(HEARTBEAT_INTERVAL_S)

    def _run_task(self, task):
        op = task.get("op")
        tid = task.get("task_id")
        started = time.time()
        try:
            if run_model is not None and op != "echo":
                result = run_model(op, task.get("payload") or {})   # real op (Eswar)
            else:
                time.sleep(0.4)                                     # stub until models/ lands
                result = {"note": f"{op} (stub) on {self.device_id}", "echo": task.get("payload")}
            status, err = RESULT_OK, None
        except Exception as e:
            result, status, err = None, RESULT_ERROR, str(e)
        finished = time.time()
        self.client.publish(topic_result(tid), json.dumps({
            "task_id": tid, "request_id": task.get("request_id"), "device_id": self.device_id,
            "op": op, "status": status, "result": result,
            "started_ts": started, "finished_ts": finished,
            "latency_ms": round((finished - started) * 1000, 1), "error": err,
        }))
        print(f"[{self.device_id}] ran {op} ({tid}) -> {status}", flush=True)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    cfg = load_config(argv[1])
    agent = Agent(cfg)
    agent.start()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    try:
        while not stop.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        agent.stop()
        print(f"[{cfg['device_id']}] stopped", flush=True)


if __name__ == "__main__":
    main(sys.argv)
