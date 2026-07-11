"""Manual smoke check for models.run_model — v2 triage, no broker/engine needed.

Run from the repo root either way:
    python -m models.smoke_check
    python models/smoke_check.py

The local tiers need an OpenAI-compatible server at NEURAROUTE_LOCAL_BASE_URL
(LM Studio / llama.cpp / the dev mock on :1234); the cloud tier uses mock mode by
default. Without a server the local ops return the standard error envelope (never crash).
"""
import json
import os
import sys

# make `models` importable even when run as `python models/smoke_check.py`
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from models import run_model
from models.tripwire import tripwire

PROFILE = {
    "patient_id": "P-03", "name": "Abdul Karim", "age": 58,
    "conditions": ["Post-MI (heart attack 2024)"],
    "baseline": {"hr": 64, "spo2": 97, "temp_c": 36.7, "resp_rate": 14},
    "history_summary": "Heart attack in 2024. On beta-blocker, baseline HR 60-68. HR above 110 is a red flag.",
}

CASES = [
    ("normal reading, cloud tier (mock GPT)", "cloud-01",
     {"hr": 66, "spo2": 97, "temp_c": 36.8, "resp_rate": 14}),
    ("borderline reading, pc tier (local LLM)", "pc-01",
     {"hr": 112, "spo2": 94, "temp_c": 37.9, "resp_rate": 19}),
    ("extreme reading, arduino tier (SLM)", "arduino-01",
     {"hr": 176, "spo2": 79, "temp_c": 37.0, "resp_rate": 32}),
]

for label, device, vitals in CASES:
    print("=" * 80)
    print(f"{label}  |  tripwire says: {tripwire(vitals)}")
    out = run_model("triage", {"patient_id": "P-03", "vitals": vitals, "profile": PROFILE},
                    device=device)
    print(json.dumps(out, indent=2)[:1200])
