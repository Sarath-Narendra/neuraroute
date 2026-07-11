#!/usr/bin/env python3
"""fake_device.py -- simulated NeuraRoute device node(s).

Publishes heartbeats (with drifting battery/load) to neuraroute/heartbeat every ~1.5 s,
and executes any task dispatched to neuraroute/task/<device_id> after a fake, op-dependent
delay -- publishing the result to neuraroute/result/<task_id>. This is what the engine and
runtime devs build against with no real hardware.

Usage (run from repo root):
    python -m contracts.fake_device pc-01
    python -m contracts.fake_device pc-01 phone-01 cloud-01
    NEURAROUTE_BROKER=192.168.1.5 python -m contracts.fake_device phone-01

Kill a device's process (Ctrl-C, or scripts/kill_device.sh <id>) and the engine will mark
it stale after STALE_TIMEOUT_S -- that's the failover trigger.

Admin (publish to neuraroute/admin):
    {"cmd": "simulate_battery_critical", "device_id": "phone-01"}
    {"cmd": "reset", "device_id": "phone-01"}
"""
import json
import random
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt

from contracts.topics import (
    BROKER_PORT, HEARTBEAT_INTERVAL_S, TOPIC_ADMIN, TOPIC_HEARTBEAT,
    broker_host, topic_result, topic_task,
    OP_EXTRACT_TEXT, OP_SUMMARIZE, OP_FLAG_RISK, OP_PATIENT_EXPLAINER,
    OP_POPULATION_STATS, OP_ECHO, RESULT_OK,
)

# --- built-in device roster: `fake_device.py pc-01` knows pc-01's shape ---------------
ROSTER = {
    "pc-01": dict(accelerators=["cpu", "npu"],
                  models=[OP_EXTRACT_TEXT, OP_SUMMARIZE, OP_FLAG_RISK, OP_PATIENT_EXPLAINER],
                  battery=None, privacy_ok=True, base_latency_ms=8),
    "phone-01": dict(accelerators=["cpu", "npu"],
                     models=[OP_SUMMARIZE, OP_FLAG_RISK, OP_PATIENT_EXPLAINER],
                     battery=dict(percent=78.0, charging=False), privacy_ok=True, base_latency_ms=20),
    "arduino-01": dict(accelerators=["cpu"],
                       models=[OP_FLAG_RISK, OP_ECHO],
                       battery=None, privacy_ok=True, base_latency_ms=35),
    "cloud-01": dict(accelerators=["cpu", "gpu"],
                     models=[OP_SUMMARIZE, OP_POPULATION_STATS, OP_PATIENT_EXPLAINER],
                     battery=None, privacy_ok=False, base_latency_ms=90),
}
DEFAULT_SPEC = dict(accelerators=["cpu"], models=[OP_ECHO], battery=None,
                    privacy_ok=True, base_latency_ms=25)

# fake execution time per op (seconds)
OP_DELAY = {
    OP_EXTRACT_TEXT: 0.8, OP_SUMMARIZE: 2.5, OP_FLAG_RISK: 1.8,
    OP_PATIENT_EXPLAINER: 2.2, OP_POPULATION_STATS: 1.5, OP_ECHO: 0.3,
}


class DeviceSim:
    def __init__(self, device_id: str):
        spec = dict(ROSTER.get(device_id, DEFAULT_SPEC))
        self.device_id = device_id
        self.accelerators = spec["accelerators"]
        self.models = spec["models"]
        self.privacy_ok = spec["privacy_ok"]
        self.base_latency_ms = spec["base_latency_ms"]
        self.battery = dict(spec["battery"]) if spec["battery"] else None
        self.cpu_load = random.uniform(0.1, 0.3)
        self.npu_load = random.uniform(0.05, 0.2)
        self._running = True
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"fake-{device_id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    # --- lifecycle ---
    def start(self):
        # connect_async + auto-reconnect: survives broker-not-ready-yet and broker restarts
        self.client.reconnect_delay_set(min_delay=1, max_delay=5)
        self.client.connect_async(broker_host(), BROKER_PORT, keepalive=15)
        self.client.loop_start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        print(f"[{self.device_id}] up  (accel={self.accelerators} models={self.models} "
              f"privacy_ok={self.privacy_ok})", flush=True)

    def stop(self):
        self._running = False
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    # --- mqtt callbacks ---
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        client.subscribe(topic_task(self.device_id))
        client.subscribe(TOPIC_ADMIN)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
        except Exception:
            return
        if msg.topic == TOPIC_ADMIN:
            self._handle_admin(data)
        elif msg.topic == topic_task(self.device_id):
            threading.Thread(target=self._run_task, args=(data,), daemon=True).start()

    def _handle_admin(self, data):
        if data.get("device_id") not in (None, self.device_id):
            return
        cmd = data.get("cmd")
        if cmd == "simulate_battery_critical":
            self.battery = dict(percent=4.0, charging=False)
            print(f"[{self.device_id}] !! battery critical (4%)", flush=True)
        elif cmd == "reset":
            spec = ROSTER.get(self.device_id, DEFAULT_SPEC)
            self.battery = dict(spec["battery"]) if spec["battery"] else None
            print(f"[{self.device_id}] reset", flush=True)

    # --- work ---
    def _run_task(self, task):
        op = task.get("op", OP_ECHO)
        started = time.time()
        delay = OP_DELAY.get(op, 1.0) * random.uniform(0.85, 1.15)
        self.npu_load = min(1.0, self.npu_load + 0.4)
        time.sleep(delay)
        self.npu_load = max(0.05, self.npu_load - 0.4)
        finished = time.time()
        result = {
            "task_id": task.get("task_id"),
            "request_id": task.get("request_id"),
            "device_id": self.device_id,
            "op": op,
            "status": RESULT_OK,
            "result": {"note": f"{op} done by {self.device_id}", "echo": task.get("payload")},
            "started_ts": started,
            "finished_ts": finished,
            "latency_ms": round((finished - started) * 1000, 1),
            "error": None,
        }
        self.client.publish(topic_result(task.get("task_id", "unknown")), json.dumps(result))
        print(f"[{self.device_id}] ran {op} ({task.get('task_id')}) in {result['latency_ms']:.0f} ms", flush=True)

    # --- heartbeat ---
    def _heartbeat_loop(self):
        while self._running:
            self._drift()
            hb = {
                "device_id": self.device_id,
                "ts": time.time(),
                "accelerators": self.accelerators,
                "models": self.models,
                "battery": (dict(percent=round(self.battery["percent"], 1),
                                 charging=self.battery["charging"]) if self.battery else None),
                "cpu_load": round(self.cpu_load, 3),
                "npu_load": round(self.npu_load, 3),
                "ram_free_mb": random.randint(2000, 20000),
                "net": {"reachable": True, "latency_ms": self.base_latency_ms + random.randint(0, 10)},
                "privacy_ok": self.privacy_ok,
                "telemetry_mode": "simulated",
            }
            self.client.publish(TOPIC_HEARTBEAT, json.dumps(hb))
            time.sleep(HEARTBEAT_INTERVAL_S)

    def _drift(self):
        # random-walk the load; slowly drain a discharging battery
        self.cpu_load = min(1.0, max(0.02, self.cpu_load + random.uniform(-0.05, 0.05)))
        self.npu_load = min(1.0, max(0.02, self.npu_load + random.uniform(-0.05, 0.05)))
        if self.battery and not self.battery["charging"]:
            self.battery["percent"] = max(1.0, self.battery["percent"] - 0.1)


def main(argv):
    device_ids = argv[1:]
    if not device_ids:
        print(__doc__)
        sys.exit(1)
    sims = [DeviceSim(d) for d in device_ids]
    for s in sims:
        s.start()

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    try:
        while not stop.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for s in sims:
            s.stop()
        print("[fake_device] stopped", flush=True)


if __name__ == "__main__":
    main(sys.argv)
