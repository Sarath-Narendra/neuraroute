#!/usr/bin/env python3
"""NeuraRoute Decision Engine v2 — vitals triage down the connectivity ladder.

What it does:
  * subscribes to neuraroute/heartbeat, tracks tier liveness (3 s stale timeout)
  * POST /request takes a reading {patient_id, vitals} -> one triage task, dispatched
    to the highest alive tier (cloud -> pc -> phone -> arduino); stale/error/timeout
    cascades down the ladder
  * fans every raw reading out on neuraroute/reading (the arduino watchdog's input)
  * forwards watchdog alerts from neuraroute/sos to every UI as an `sos` event
  * re-broadcasts every engine event to neuraroute/event AND to connected apps over /ws
  * HTTP: GET /health, /devices, /patients, /status ; POST /request ; WS /ws

Run from repo root:
    python -m engine.app
    NEURAROUTE_BROKER=192.168.1.5 NEURAROUTE_PORT=8000 python -m engine.app
"""
import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from contracts.topics import (
    BROKER_PORT, CONTRACTS_VERSION, EV_SOS, TOPIC_EVENT, TOPIC_HEARTBEAT,
    TOPIC_READING, TOPIC_RESULT_WILDCARD, TOPIC_SOS, broker_host,
)
from engine.orchestrator import Orchestrator
from engine.resource_graph import ResourceGraph
from engine.scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("engine")

graph = ResourceGraph()
_ws_clients: set[WebSocket] = set()
_main_loop: asyncio.AbstractEventLoop | None = None
_mqtt: mqtt.Client | None = None
scheduler: Scheduler | None = None
orchestrator: Orchestrator | None = None


# --- patient records (the ward roster; each tier also carries its own local copy) ----
def _records_path() -> Path:
    env = os.environ.get("NEURAROUTE_RECORDS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "patients.json"


def _load_patients() -> dict:
    try:
        with open(_records_path()) as f:
            return {p["patient_id"]: p for p in json.load(f)}
    except Exception:
        log.exception("could not load patient records from %s — running with none", _records_path())
        return {}


PATIENTS = _load_patients()


# --- event fan-out: MQTT (neuraroute/event) + every connected app --------------------
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
    client.subscribe(TOPIC_SOS)


def _on_message(client, userdata, msg):
    try:
        if msg.topic == TOPIC_HEARTBEAT:
            event = graph.update(json.loads(msg.payload))
            if event:
                log.info("device %s ALIVE", event["device_id"])
                emit_event(event)
        elif msg.topic == TOPIC_SOS:
            # the always-on watchdog raised an extreme emergency — forward to every app
            sos = json.loads(msg.payload)
            sos.setdefault("type", EV_SOS)
            sos.setdefault("ts", time.time())
            log.warning("SOS from %s: patient %s — %s",
                        sos.get("source", "?"), sos.get("patient_id"), sos.get("reason"))
            emit_event(sos)
        elif msg.topic.startswith("neuraroute/result/"):
            res = json.loads(msg.payload)
            log.info("result %s from %s: %s (%.0f ms)", res.get("task_id"), res.get("device_id"),
                     res.get("status"), res.get("latency_ms") or 0)
            if orchestrator is not None and _main_loop is not None:
                _main_loop.call_soon_threadsafe(orchestrator.on_result, res)
    except Exception:
        log.exception("bad message on %s", msg.topic)


# --- monitor loop: age tiers out, emit stale events -----------------------------------
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
    global _main_loop, _mqtt, scheduler, orchestrator
    _main_loop = asyncio.get_running_loop()
    _mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="neuraroute-engine")
    _mqtt.on_connect = _on_connect
    _mqtt.on_message = _on_message
    # connect_async + auto-reconnect: broker can start after us and restart under us
    _mqtt.reconnect_delay_set(min_delay=1, max_delay=5)
    _mqtt.connect_async(broker_host(), BROKER_PORT, keepalive=30)
    _mqtt.loop_start()
    scheduler = Scheduler(graph)
    orchestrator = Orchestrator(graph, scheduler,
                                publish=lambda topic, payload: _mqtt.publish(topic, payload),
                                emit=emit_event, loop=_main_loop)
    monitor = asyncio.create_task(_monitor())
    log.info("NeuraRoute engine up (contracts v%s, %d patients on file) -- waiting for heartbeats",
             CONTRACTS_VERSION, len(PATIENTS))
    try:
        yield
    finally:
        monitor.cancel()
        _mqtt.loop_stop()
        _mqtt.disconnect()


app = FastAPI(title="NeuraRoute Engine", version=CONTRACTS_VERSION, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "contracts": CONTRACTS_VERSION,
            "patients": len(PATIENTS), "devices": graph.summary()}


@app.get("/devices")
def devices():
    return graph.summary()


@app.get("/patients")
def patients():
    """The ward roster — the phone app builds its 10 patient cards from this."""
    return list(PATIENTS.values())


@app.post("/request", status_code=202)
async def create_request(req: Request):
    """One sensor reading: {patient_id, vitals: {hr, spo2, temp_c, resp_rate, ...}}.

    Kicks off a triage run down the ladder AND fans the raw reading out on
    neuraroute/reading for the always-on arduino watchdog.
    """
    try:
        body = await req.json()
    except Exception:
        body = {}
    body = body or {}
    patient_id = str(body.get("patient_id") or "unknown")
    vitals = body.get("vitals") or {}
    if not isinstance(vitals, dict):
        return {"accepted": False, "error": "vitals must be an object"}
    request_id = body.get("request_id") or f"req-{uuid.uuid4().hex[:6]}"
    profile = PATIENTS.get(patient_id, {})
    if not profile:
        log.warning("reading for unknown patient %s — triaging without a record", patient_id)

    # safety path: raw reading to the watchdog, no matter what the ladder does
    _mqtt.publish(TOPIC_READING, json.dumps(
        {"patient_id": patient_id, "vitals": vitals, "ts": time.time(), "request_id": request_id}))

    orchestrator.start_run(request_id, patient_id=patient_id, vitals=vitals, profile=profile)
    log.info("POST /request -> %s (patient=%s)", request_id, patient_id)
    return {"accepted": True, "request_id": request_id, "patient_id": patient_id}


@app.get("/status")
def status():
    return orchestrator.status() if orchestrator else {}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    log.info("app connected (%d total)", len(_ws_clients))
    try:
        for snap in graph.alive_snapshot_events():  # bring the new client up to date
            await websocket.send_text(json.dumps(snap))
        while True:
            await websocket.receive_text()  # ignore inbound; keeps the socket open
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        log.info("app disconnected (%d left)", len(_ws_clients))


def main():
    import uvicorn
    # 8080 by default: the inference module's /infer servers own 8000 (laptop) and 8001 (cloud).
    port = int(os.environ.get("NEURAROUTE_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    main()
