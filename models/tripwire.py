"""
models/tripwire.py

The failsafe's hard numeric safety floor. Pure Python — no model, no network, never
raises. The always-on arduino watchdog runs this on EVERY reading before/alongside
the SLM: a tiny model can hallucinate "normal" on a dying patient; these bounds can't.

This is deliberately NOT a scoring system (no NEWS2, no points): just hard "this is
never fine" limits. Everything subtler is the models' job.
"""

# Any single breach -> extreme emergency. Bounds are deliberately loose so they only
# fire on unambiguous, life-threatening readings; the LLM/SLM handles the grey zone.
BOUNDS = {
    "hr":        {"low": 40,   "high": 135,  "unit": "bpm"},
    "spo2":      {"low": 85,   "high": None, "unit": "%"},
    "temp_c":    {"low": 34.0, "high": 40.0, "unit": "C"},
    "resp_rate": {"low": 8,    "high": 30,   "unit": "/min"},
    "bp_sys":    {"low": 80,   "high": 200,  "unit": "mmHg"},
}

SEV_EMERGENCY = "emergency"
SEV_NORMAL = "normal"


def tripwire(vitals: dict) -> tuple[str, list[str]]:
    """Return ("emergency", [human-readable reasons]) if any hard bound is breached,
    else ("normal", []). Unknown/missing/garbage fields are skipped, never fatal."""
    reasons = []
    if not isinstance(vitals, dict):
        return SEV_NORMAL, []
    for key, b in BOUNDS.items():
        raw = vitals.get(key)
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if b["low"] is not None and v < b["low"]:
            reasons.append(f"{key} {v:g} < {b['low']:g} {b['unit']}")
        if b["high"] is not None and v > b["high"]:
            reasons.append(f"{key} {v:g} > {b['high']:g} {b['unit']}")
    return (SEV_EMERGENCY, reasons) if reasons else (SEV_NORMAL, [])
