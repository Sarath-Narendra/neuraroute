#!/usr/bin/env python3
"""NeuraRoute Decision Engine -- Day-1 skeleton.

What works today:
  * subscribes to neuraroute/heartbeat, builds an in-memory Resource Graph
  * logs and emits device_alive / device_stale transitions (3 s timeout)
  * re-broadcasts every engine event to neuraroute/event AND to connected dashboards over /ws
  * HTTP: GET /health, GET /devices, POST /request (stub), WS /ws

Coming Friday (P1): scheduler cost function, hardcoded DAG planner, dispatch, failover.

Run from repo root:
    python -m engine.app
    NEURAROUTE_BROKER=192.168.1.5 NEURAROUTE_PORT=8000 python -m engine.app
"""
import asyncio
import base64
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from contracts.topics import (
    BROKER_PORT, CONTRACTS_VERSION, EV_POLICY, TOPIC_EVENT, TOPIC_HEARTBEAT,
    TOPIC_RESULT_WILDCARD, broker_host,
)
from engine.orchestrator import Orchestrator
from engine.policy import Policy
from engine.resource_graph import ResourceGraph
from engine.scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("engine")

graph = ResourceGraph()
_ws_clients: set[WebSocket] = set()
_main_loop: asyncio.AbstractEventLoop | None = None
_mqtt: mqtt.Client | None = None
policy: Policy | None = None
scheduler: Scheduler | None = None
orchestrator: Orchestrator | None = None


# --- event fan-out: MQTT (neuraroute/event) + every connected dashboard --------------
def emit_event(event: dict):
    payload = json.dumps(event)
    if _mqtt is not None:
        _mqtt.publish(TOPIC_EVENT, payload)
    # hop from whatever thread we're on back to the asyncio loop for the WS sends
    if _main_loop is not None and _ws_clients:
        _main_loop.call_soon_threadsafe(_schedule_broadcast, payload)


def _schedule_broadcast(payload: str):
    for ws in list(_ws_clients):
        asyncio.create_task(_safe_send(ws, payload))


async def _safe_send(ws: WebSocket, payload: str):
    try:
        await ws.send_text(payload)
    except Exception:
        _ws_clients.discard(ws)


# --- MQTT callbacks (run on paho's network thread) -----------------------------------
def _on_connect(client, userdata, flags, reason_code, properties=None):
    log.info("connected to broker %s:%s (rc=%s)", broker_host(), BROKER_PORT, reason_code)
    client.subscribe(TOPIC_HEARTBEAT)
    client.subscribe(TOPIC_RESULT_WILDCARD)


def _on_message(client, userdata, msg):
    try:
        if msg.topic == TOPIC_HEARTBEAT:
            hb = json.loads(msg.payload)
            device_id = hb.get("device_id", "<unknown>")
            battery = hb.get("battery")
            cpu_load = hb.get("cpu_load")
            npu_load = hb.get("npu_load")
            ts = hb.get("ts")
            log.info("heartbeat from %s at %s | battery=%s | cpu_load=%s | npu_load=%s",
                     device_id, ts, battery, cpu_load, npu_load)
            event = graph.update(hb)
            if event:
                log.info("device %s ALIVE", event["device_id"])
                emit_event(event)
        elif msg.topic.startswith("neuraroute/result/"):
            res = json.loads(msg.payload)
            log.info("result %s from %s: %s (%.0f ms)", res.get("task_id"), res.get("device_id"),
                     res.get("status"), res.get("latency_ms") or 0)
            if orchestrator is not None and _main_loop is not None:
                _main_loop.call_soon_threadsafe(orchestrator.on_result, res)
    except Exception:
        log.exception("bad message on %s", msg.topic)


# --- monitor loop: age devices out, emit stale events --------------------------------
async def _monitor():
    while True:
        for event in graph.tick():
            log.warning("device %s STALE", event["device_id"])
            emit_event(event)
            if orchestrator is not None:
                orchestrator.on_device_stale(event["device_id"])   # re-route its in-flight tasks
        await asyncio.sleep(1.0)


# --- app lifespan --------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop, _mqtt, policy, scheduler, orchestrator
    _main_loop = asyncio.get_running_loop()
    _mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="neuraroute-engine")
    _mqtt.on_connect = _on_connect
    _mqtt.on_message = _on_message
    # connect_async + auto-reconnect: broker can start after us and restart under us (chaos test)
    _mqtt.reconnect_delay_set(min_delay=1, max_delay=5)
    _mqtt.connect_async(broker_host(), BROKER_PORT, keepalive=30)
    _mqtt.loop_start()
    policy = Policy()
    scheduler = Scheduler(graph, policy)
    orchestrator = Orchestrator(graph, scheduler,
                                publish=lambda topic, payload: _mqtt.publish(topic, payload),
                                emit=emit_event, loop=_main_loop)
    monitor = asyncio.create_task(_monitor())
    log.info("NeuraRoute engine up (contracts v%s, policy=%s) -- waiting for heartbeats",
             CONTRACTS_VERSION, policy.active_profile)
    try:
        yield
    finally:
        monitor.cancel()
        _mqtt.loop_stop()
        _mqtt.disconnect()


app = FastAPI(title="NeuraRoute Engine", version=CONTRACTS_VERSION, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "contracts": CONTRACTS_VERSION, "devices": graph.summary()}


@app.get("/devices")
def devices():
    return graph.summary()


@app.post("/request", status_code=202)
async def create_request(req: Request):
    """Upload a PDF (multipart form field `file`) from the phone browser -> orchestrated DAG run.

    Also accepts a JSON body or an empty body to trigger a run with no file (demo/tests) —
    in that case the entry task gets a placeholder document descriptor.
    """
    document = None
    request_id = None
    if req.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await req.form()
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            data = await upload.read()
            document = {"filename": upload.filename or "upload.pdf", "bytes": len(data),
                        "pdf_b64": base64.b64encode(data).decode()}
        request_id = form.get("request_id")
    else:
        try:
            body = await req.json()
        except Exception:
            body = {}
        request_id = (body or {}).get("request_id")

    request_id = request_id or f"req-{uuid.uuid4().hex[:6]}"
    orchestrator.start_run(request_id, document=document)
    log.info("POST /request -> %s (file=%s)", request_id, document and document["filename"])
    resp = {"accepted": True, "request_id": request_id}
    if document:
        resp["document"] = {"filename": document["filename"], "bytes": document["bytes"]}
    return resp


@app.post("/policy")
async def set_policy(body: dict):
    """Flip the scheduler profile live (speed_first <-> battery_saver) — the demo toggle."""
    profile = (body or {}).get("profile", "")
    if not policy.set_profile(profile):
        return {"ok": False, "error": f"unknown profile '{profile}'"}
    emit_event({"type": EV_POLICY, "ts": time.time(), "reason": f"policy -> {profile}",
                "profile": profile})
    log.info("policy flipped -> %s %s", profile, policy.weights())
    return {"ok": True, "active_profile": profile, "weights": policy.weights()}


@app.get("/status")
def status():
    return orchestrator.status() if orchestrator else {}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    log.info("dashboard connected (%d total)", len(_ws_clients))
    try:
        for snap in graph.alive_snapshot_events():  # bring the new client up to date
            await websocket.send_text(json.dumps(snap))
        while True:
            await websocket.receive_text()  # ignore inbound; keeps the socket open
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        log.info("dashboard disconnected (%d left)", len(_ws_clients))


def main():
    import uvicorn
    port = int(os.environ.get("NEURAROUTE_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    main()
