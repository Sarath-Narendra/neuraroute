"""Scheduler: pick the best device for a task.

Two stages:
  1. Feasibility filter (HARD constraints) — alive, advertises the op, and the privacy
     rule: a `sensitive` task may only run where privacy_ok is true (never the cloud).
  2. Cost function over live telemetry — Cost = wL·latency + wE·energy + wC·cloud − wP·privacy,
     normalized across the feasible candidates; argmin wins. Every choice comes back with a
     human-readable reason for the projector.

A small parallel-spread penalty nudges concurrently-ready tasks (t2 ∥ t3) onto different
devices without hard-excluding — so if only one device is feasible, the task still runs.
"""
from contracts.topics import PRIVACY_SENSITIVE

PARALLEL_PENALTY = 0.5   # added to a device already running another task in this wave


def _latency_raw(hb: dict) -> float:
    net = hb.get("net") or {}
    latency = float(net.get("latency_ms", 20))
    busy = max(float(hb.get("cpu_load", 0.0)), float(hb.get("npu_load", 0.0)))
    return latency + 120.0 * busy          # a loaded device is effectively slower


def _energy_raw(hb: dict) -> float:
    bat = hb.get("battery")
    if not bat:
        return 0.10                        # mains-powered (PC / cloud): cheap
    if bat.get("charging"):
        return 0.20
    pct = float(bat.get("percent", 100))
    return 0.30 + 0.70 * (1.0 - pct / 100.0)   # discharging: rises as the battery drains


def _cloud_raw(hb: dict) -> float:
    return 0.0 if hb.get("privacy_ok", True) else 1.0   # off-device == cloud == monetary cost


def _privacy_raw(hb: dict) -> float:
    return 1.0 if hb.get("privacy_ok", True) else 0.0


def _norm(vals: dict) -> dict:
    lo, hi = min(vals.values()), max(vals.values())
    if hi - lo < 1e-9:
        return {k: 0.0 for k in vals}
    return {k: (v - lo) / (hi - lo) for k, v in vals.items()}


class Scheduler:
    def __init__(self, graph, policy):
        self.graph = graph
        self.policy = policy

    def feasible(self, task: dict, exclude: set) -> dict:
        """device_id -> heartbeat, for every device that can legally run this task."""
        out = {}
        for did, d in self.graph.snapshot_alive().items():
            if did in exclude:
                continue
            hb = d["hb"]
            if task["op"] not in (hb.get("models") or []):
                continue
            if task.get("privacy") == PRIVACY_SENSITIVE and not hb.get("privacy_ok", False):
                continue                    # hard privacy constraint: sensitive never leaves-device
            out[did] = hb
        return out

    def choose_device(self, task: dict, exclude: set = None, busy: set = None):
        """Return (device_id, cost, breakdown, reason) or None if nothing is feasible."""
        exclude = exclude or set()
        busy = busy or set()
        cands = self.feasible(task, exclude)
        if not cands:
            return None

        lat = _norm({d: _latency_raw(hb) for d, hb in cands.items()})
        eng = _norm({d: _energy_raw(hb) for d, hb in cands.items()})
        w = self.policy.weights()

        scored = {}
        breakdowns = {}
        for d, hb in cands.items():
            cloud = _cloud_raw(hb)
            priv = _privacy_raw(hb)
            cost = (w["wL"] * lat[d] + w["wE"] * eng[d] + w["wC"] * cloud - w["wP"] * priv)
            if d in busy:
                cost += PARALLEL_PENALTY
            scored[d] = cost
            breakdowns[d] = {"latency": round(lat[d], 2), "energy": round(eng[d], 2),
                             "cloud": cloud, "privacy": priv, "cost": round(cost, 3)}

        best = min(scored, key=scored.get)
        hb = cands[best]
        bd = breakdowns[best]
        placement = "cloud" if not hb.get("privacy_ok", True) else "on-device"
        if task.get("privacy") == PRIVACY_SENSITIVE:
            placement = "on-device (sensitive)"
        reason = (f"{best}: {placement}, {task['op']} — cost {bd['cost']:.2f} "
                  f"[L {bd['latency']}·{w['wL']} E {bd['energy']}·{w['wE']} "
                  f"C {bd['cloud']}·{w['wC']} −P {bd['privacy']}·{w['wP']}]"
                  f"{' (+parallel)' if best in busy else ''}")
        return best, scored[best], bd, reason
