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
import json
import logging
import os
from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from contracts.topics import (
    BROKER_PORT, CONTRACTS_VERSION, TOPIC_EVENT, TOPIC_HEARTBEAT,
    TOPIC_RESULT_WILDCARD, broker_host,
)
from engine.resource_graph import ResourceGraph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("engine")

graph = ResourceGraph()
_ws_clients: set[WebSocket] = set()
_main_loop: asyncio.AbstractEventLoop | None = None
_mqtt: mqtt.Client | None = None


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
            event = graph.update(json.loads(msg.payload))
            if event:
                log.info("device %s ALIVE", event["device_id"])
                emit_event(event)
        elif msg.topic.startswith("neuraroute/result/"):
            res = json.loads(msg.payload)
            log.info("result %s from %s: %s (%.0f ms)", res.get("task_id"), res.get("device_id"),
                     res.get("status"), res.get("latency_ms") or 0)
    except Exception:
        log.exception("bad message on %s", msg.topic)


# --- monitor loop: age devices out, emit stale events --------------------------------
async def _monitor():
    while True:
        for event in graph.tick():
            log.warning("device %s STALE", event["device_id"])
            emit_event(event)
        await asyncio.sleep(1.0)


# --- app lifespan --------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop, _mqtt
    _main_loop = asyncio.get_running_loop()
    _mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="neuraroute-engine")
    _mqtt.on_connect = _on_connect
    _mqtt.on_message = _on_message
    # connect_async + auto-reconnect: broker can start after us and restart under us (chaos test)
    _mqtt.reconnect_delay_set(min_delay=1, max_delay=5)
    _mqtt.connect_async(broker_host(), BROKER_PORT, keepalive=30)
    _mqtt.loop_start()
    monitor = asyncio.create_task(_monitor())
    log.info("NeuraRoute engine up (contracts v%s) -- waiting for heartbeats", CONTRACTS_VERSION)
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
async def request(body: dict | None = None):
    # Friday: turn this into the hardcoded DAG plan + dispatch. Today it just acknowledges.
    log.info("POST /request received: %s", body)
    return {"accepted": True, "note": "planner + dispatch land Friday (P1)"}


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
