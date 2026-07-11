#!/usr/bin/env python3
"""fake_engine.py -- canned decision-event stream for dashboard development.

Serves a WebSocket at ws://<host>:8000/ws (the SAME interface the real engine exposes)
and replays a realistic storyboard of a full run: 4 devices come alive, a health-report
request fans out across the 5-task DAG, t2 and t3 run in parallel on different devices,
one device is killed mid-run and its task migrates live, then metrics land. Loops forever.

No broker required -- the dashboard dev just points their WebSocket client here.

Usage (run from repo root):
    python -m contracts.fake_engine
    python -m contracts.fake_engine --port 8000

Events conform to contracts/event.schema.json.
"""
import argparse
import asyncio
import json
import time

import websockets

from contracts.topics import (
    EV_DEVICE_ALIVE, EV_REQUEST_START, EV_PLACEMENT, EV_TASK_START, EV_TASK_DONE,
    EV_FAILOVER, EV_METRICS, EV_REQUEST_DONE,
    OP_EXTRACT_TEXT, OP_SUMMARIZE, OP_FLAG_RISK, OP_PATIENT_EXPLAINER, OP_POPULATION_STATS,
)

REQ = "req-demo"


def ev(**kw):
    kw.setdefault("ts", time.time())
    return kw


# (event, seconds-to-wait-after-sending) -- one pass of the storyboard
def storyboard():
    devices = [
        ("pc-01", ["cpu", "npu"], True),
        ("phone-01", ["cpu", "npu"], True),
        ("arduino-01", ["cpu"], True),
        ("cloud-01", ["cpu", "gpu"], False),
    ]
    steps = []
    for did, accel, priv in devices:
        steps.append((ev(type=EV_DEVICE_ALIVE, device_id=did,
                         reason=f"{did} joined ({','.join(accel)})",
                         heartbeat={"accelerators": accel, "privacy_ok": priv,
                                    "battery": {"percent": 78, "charging": False} if did == "phone-01" else None}), 0.4))

    steps.append((ev(type=EV_REQUEST_START, request_id=REQ,
                     reason="health-report.pdf uploaded from phone -> 5-task DAG"), 0.6))

    # t1 extract_text on pc-01
    steps.append((ev(type=EV_PLACEMENT, request_id=REQ, task_id=f"{REQ}-t1", op=OP_EXTRACT_TEXT,
                     device_id="pc-01", reason="pc-01: PyMuPDF, NPU free, on-device (sensitive)"), 0.2))
    steps.append((ev(type=EV_TASK_START, request_id=REQ, task_id=f"{REQ}-t1", op=OP_EXTRACT_TEXT, device_id="pc-01"), 0.9))
    steps.append((ev(type=EV_TASK_DONE, request_id=REQ, task_id=f"{REQ}-t1", op=OP_EXTRACT_TEXT, device_id="pc-01",
                     reason="extracted 1,240 words"), 0.3))

    # t2 || t3 -- parallel, different devices (the money shot)
    steps.append((ev(type=EV_PLACEMENT, request_id=REQ, task_id=f"{REQ}-t2", op=OP_SUMMARIZE, device_id="phone-01",
                     reason="phone-01: on-device (sensitive), NPU free, lowest energy",
                     score={"latency": 0.4, "energy": 0.2, "cost": 0.0, "privacy": 1.0, "total": 0.31}), 0.15))
    steps.append((ev(type=EV_PLACEMENT, request_id=REQ, task_id=f"{REQ}-t3", op=OP_FLAG_RISK, device_id="pc-01",
                     reason="pc-01: parallel with t2 on a DIFFERENT device, NPU headroom",
                     score={"latency": 0.3, "energy": 0.3, "cost": 0.0, "privacy": 1.0, "total": 0.29}), 0.3))
    steps.append((ev(type=EV_TASK_START, request_id=REQ, task_id=f"{REQ}-t2", op=OP_SUMMARIZE, device_id="phone-01"), 0.1))
    steps.append((ev(type=EV_TASK_START, request_id=REQ, task_id=f"{REQ}-t3", op=OP_FLAG_RISK, device_id="pc-01"), 1.0))

    # THE KILL: phone-01 drops mid-summarize -> t2 migrates to cloud-01
    steps.append((ev(type=EV_FAILOVER, request_id=REQ, task_id=f"{REQ}-t2", op=OP_SUMMARIZE,
                     from_device="phone-01", device_id="cloud-01",
                     reason="phone-01 missed heartbeat (>3s) -> re-route t2 to cloud-01 (public? no -> next on-device: none free -> cloud fallback)"), 0.4))
    steps.append((ev(type=EV_TASK_DONE, request_id=REQ, task_id=f"{REQ}-t3", op=OP_FLAG_RISK, device_id="pc-01",
                     reason="risk: LOW"), 0.3))
    steps.append((ev(type=EV_TASK_START, request_id=REQ, task_id=f"{REQ}-t2", op=OP_SUMMARIZE, device_id="cloud-01"), 1.2))
    steps.append((ev(type=EV_TASK_DONE, request_id=REQ, task_id=f"{REQ}-t2", op=OP_SUMMARIZE, device_id="cloud-01",
                     reason="summary ready (recovered)"), 0.3))

    # t5 population_stats (public -> cloud-eligible)
    steps.append((ev(type=EV_PLACEMENT, request_id=REQ, task_id=f"{REQ}-t5", op=OP_POPULATION_STATS, device_id="cloud-01",
                     reason="cloud-01: public data, cloud-eligible, aggregate stats"), 0.2))
    steps.append((ev(type=EV_TASK_START, request_id=REQ, task_id=f"{REQ}-t5", op=OP_POPULATION_STATS, device_id="cloud-01"), 0.8))
    steps.append((ev(type=EV_TASK_DONE, request_id=REQ, task_id=f"{REQ}-t5", op=OP_POPULATION_STATS, device_id="cloud-01"), 0.2))

    # t4 patient_explainer on pc-01
    steps.append((ev(type=EV_PLACEMENT, request_id=REQ, task_id=f"{REQ}-t4", op=OP_PATIENT_EXPLAINER, device_id="pc-01",
                     reason="pc-01: needs t2 & t3, on-device (sensitive)"), 0.2))
    steps.append((ev(type=EV_TASK_START, request_id=REQ, task_id=f"{REQ}-t4", op=OP_PATIENT_EXPLAINER, device_id="pc-01"), 0.9))
    steps.append((ev(type=EV_TASK_DONE, request_id=REQ, task_id=f"{REQ}-t4", op=OP_PATIENT_EXPLAINER, device_id="pc-01"), 0.3))

    steps.append((ev(type=EV_METRICS, request_id=REQ,
                     metrics={"latency_orchestrated_s": 6.4, "latency_baseline_s": 19.8, "speedup": 3.1,
                              "cloud_calls": 2, "battery_delta_pct": 3.0, "failover_time_s": 1.8}), 0.4))
    steps.append((ev(type=EV_REQUEST_DONE, request_id=REQ, reason="run complete"), 2.5))
    return steps


async def handler(websocket):
    print(f"[fake_engine] dashboard connected: {websocket.remote_address}", flush=True)
    try:
        while True:
            for event, wait in storyboard():
                await websocket.send(json.dumps(event))
                await asyncio.sleep(wait)
    except websockets.ConnectionClosed:
        print("[fake_engine] dashboard disconnected", flush=True)


async def amain(port):
    print(f"[fake_engine] serving canned events at ws://0.0.0.0:{port}/ws  (Ctrl-C to stop)", flush=True)
    async with websockets.serve(handler, "0.0.0.0", port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    try:
        asyncio.run(amain(args.port))
    except KeyboardInterrupt:
        print("\n[fake_engine] stopped", flush=True)
