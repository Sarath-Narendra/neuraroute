#!/usr/bin/env python3
"""
scripts/vitals_feed.py — the automated bedside monitor.

Streams patient vitals into the engine's POST /request on a fixed interval, exactly like
ten real bedside monitors would. This is what makes the demo run HANDS-FREE and, crucially,
OFFLINE: it runs locally on the laptop and hits localhost, so it keeps firing even when the
internet (and Claude) is gone — which is the whole point of the failover story.

Most readings are normal jitter around each patient's baseline; every Nth reading is a
deliberate emergency (trips the watchdog + makes the model shout). Nothing here needs the
internet — only the CLOUD tier does, so pulling the plug slides the ladder down to the laptop
automatically, live on the phone.

Usage:
    python scripts/vitals_feed.py                 # every 5s, an emergency every 5th reading
    python scripts/vitals_feed.py --interval 4 --emergency-every 6
    python scripts/vitals_feed.py --engine http://localhost:8080

Ctrl-C to stop.
"""
import argparse
import itertools
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_patients():
    data = json.load(open(REPO / "data" / "patients.json"))
    return [
        {"id": p["patient_id"], "name": p.get("name", p["patient_id"]),
         "base": p.get("baseline", {})}
        for p in data
    ]


def jitter(base, lo, hi, spread):
    """A believable normal reading: baseline nudged a little, clamped to a safe band.

    Deterministic wobble (no RNG) so runs are reproducible and never accidentally trip a
    tripwire — normal stays normal."""
    import math
    t = time.time()
    val = (base if base is not None else (lo + hi) / 2) + spread * math.sin(t)
    return max(lo, min(hi, val))


def normal_vitals(base):
    return {
        "hr": round(jitter(base.get("hr", 78), 60, 100, 6)),
        "spo2": round(jitter(base.get("spo2", 97), 93, 99, 1.5)),
        "temp_c": round(jitter(base.get("temp_c", 36.8), 36.4, 37.6, 0.3), 1),
        "resp_rate": round(jitter(base.get("resp_rate", 16), 12, 22, 2)),
    }


def emergency_vitals():
    """A clear crash: trips every tripwire (hr>135, spo2<85, rr>30) so the watchdog fires
    and the triage model returns emergency no matter which tier answers."""
    return {"hr": 176, "spo2": 79, "temp_c": 37, "resp_rate": 32}


def post_reading(engine, patient_id, vitals, timeout=8):
    body = json.dumps({"patient_id": patient_id, "vitals": vitals}).encode()
    req = urllib.request.Request(f"{engine}/request", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=os.environ.get("NEURAROUTE_ENGINE", "http://localhost:8080"))
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between readings")
    ap.add_argument("--emergency-every", type=int, default=5, help="every Nth reading is critical (0=never)")
    args = ap.parse_args()

    # Line-buffer stdout so the stream shows LIVE on the laptop screen even when piped to a
    # log/tee (Python fully-buffers stdout when it isn't a TTY, which hid the feed).
    try:
        import sys
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    patients = load_patients()
    print(f"[vitals_feed] {len(patients)} patients -> {args.engine}  "
          f"(every {args.interval}s, emergency every {args.emergency_every or '∞'})")
    print("[vitals_feed] runs locally — keeps streaming even with the internet off. Ctrl-C to stop.\n")

    for n, patient in enumerate(itertools.cycle(patients), start=1):
        is_emergency = args.emergency_every and (n % args.emergency_every == 0)
        vitals = emergency_vitals() if is_emergency else normal_vitals(patient["base"])
        tag = "🚨 EMERGENCY" if is_emergency else "  normal   "
        try:
            resp = post_reading(args.engine, patient["id"], vitals)
            rid = resp.get("request_id", "?")
            print(f"[{time.strftime('%H:%M:%S')}] {tag}  {patient['id']} {patient['name'][:16]:16} "
                  f"hr={vitals['hr']:>3} spo2={vitals['spo2']:>3} rr={vitals['resp_rate']:>2}  -> {rid}")
        except (urllib.error.URLError, OSError) as e:
            print(f"[{time.strftime('%H:%M:%S')}] engine unreachable ({e}); retrying next tick")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
