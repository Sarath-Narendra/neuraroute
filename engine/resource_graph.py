"""In-memory Resource Graph: live state of every device, built from heartbeats.

Thread-safe because heartbeats arrive on the paho MQTT thread while the monitor loop
(asyncio) ages devices out. Both go through the same lock. Emitting events is left to
the caller so all MQTT/WS I/O stays on well-defined threads.
"""
import threading
import time

from contracts.topics import EV_DEVICE_ALIVE, EV_DEVICE_STALE, STALE_TIMEOUT_S


class ResourceGraph:
    def __init__(self):
        self._lock = threading.Lock()
        self.devices = {}  # device_id -> {last_seen, alive, since, hb}

    def update(self, hb: dict):
        """Ingest a heartbeat. Returns a device_alive event on a stale->alive transition, else None."""
        did = hb.get("device_id")
        if not did:
            return None
        now = time.time()
        with self._lock:
            prev = self.devices.get(did)
            was_alive = bool(prev and prev["alive"])
            self.devices[did] = {
                "last_seen": now,
                "alive": True,
                "since": prev["since"] if was_alive else now,
                "hb": hb,
            }
        if not was_alive:
            accel = ",".join(hb.get("accelerators", []))
            return {"type": EV_DEVICE_ALIVE, "ts": now, "device_id": did,
                    "reason": f"{did} joined ({accel})", "heartbeat": hb}
        return None

    def tick(self, now: float | None = None):
        """Age out devices whose last heartbeat is older than STALE_TIMEOUT_S. Returns stale events."""
        now = now or time.time()
        events = []
        with self._lock:
            for did, d in self.devices.items():
                if d["alive"] and (now - d["last_seen"]) > STALE_TIMEOUT_S:
                    d["alive"] = False
                    events.append({"type": EV_DEVICE_STALE, "ts": now, "device_id": did,
                                   "reason": f"{did} missed heartbeat (>{STALE_TIMEOUT_S:.0f}s) -> quarantined"})
        return events

    def summary(self):
        with self._lock:
            return {
                did: {
                    "alive": d["alive"],
                    "last_seen": round(d["last_seen"], 2),
                    "battery": d["hb"].get("battery"),
                    "accelerators": d["hb"].get("accelerators"),
                    "models": d["hb"].get("models"),
                    "privacy_ok": d["hb"].get("privacy_ok"),
                }
                for did, d in self.devices.items()
            }

    def alive_snapshot_events(self):
        """device_alive events for every currently-live device -- sent to a freshly connected dashboard."""
        with self._lock:
            return [
                {"type": EV_DEVICE_ALIVE, "ts": d["last_seen"], "device_id": did,
                 "reason": f"{did} present", "heartbeat": d["hb"]}
                for did, d in self.devices.items() if d["alive"]
            ]
