"""Scheduler v2: the connectivity ladder.

No cost function. Two stages:
  1. Feasibility (HARD constraints) — alive, advertises the op, not excluded
     (a device gets excluded for a task after it errored/timed out on it).
  2. A fixed priority walk: cloud-01 -> pc-01 -> phone-01 -> arduino-01.
     The FIRST feasible tier wins.

Reachability IS the policy: if a higher tier is dead (missed heartbeats) or already
failed this task, the task slides down the ladder. "Internet down" surfaces as the
cloud tier erroring (its GPT call fails) or going stale — either way, next tier.
"""
from contracts.topics import PRIORITY_LADDER, TIER_LABELS


class Scheduler:
    def __init__(self, graph):
        self.graph = graph

    def feasible(self, task: dict, exclude: set) -> dict:
        """device_id -> heartbeat, for every device that can run this task right now."""
        out = {}
        for did, d in self.graph.snapshot_alive().items():
            if did in exclude:
                continue
            hb = d["hb"]
            if task["op"] not in (hb.get("models") or []):
                continue
            out[did] = hb
        return out

    def choose_device(self, task: dict, exclude: set = None, busy: set = None):
        """Return (device_id, tier_index, breakdown, reason) or None if nothing is feasible.

        `busy` is accepted for orchestrator API compat; a ladder pick deliberately does
        not avoid busy tiers — the best alive tier handles every reading.
        """
        cands = self.feasible(task, exclude or set())
        if not cands:
            return None

        for i, did in enumerate(PRIORITY_LADDER):
            if did in cands:
                skipped = PRIORITY_LADDER[:i]
                label = TIER_LABELS.get(did, did)
                reason = (f"{label}: highest tier alive"
                          + (f" — skipped {', '.join(skipped)} (down/failed)" if skipped else " (top of ladder)"))
                bd = {"tier": i + 1, "device": did, "ladder": " > ".join(PRIORITY_LADDER)}
                return did, float(i), bd, reason

        # A device outside the ladder (e.g. a second phone) is still schedulable, last.
        did = sorted(cands)[0]
        return (did, float(len(PRIORITY_LADDER)),
                {"tier": None, "device": did, "ladder": " > ".join(PRIORITY_LADDER)},
                f"{did}: outside the ladder, only feasible device")
