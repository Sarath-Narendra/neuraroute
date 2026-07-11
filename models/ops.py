"""
models/ops.py

v2: ONE op — `triage`. Cross-reference a fresh vitals reading against the patient's
record and return {patient_id, severity, transcript}. The same op runs on every tier;
only the model behind it changes (GPT on cloud, LM Studio on pc/phone, a llama.cpp
SLM on the arduino). The cloud path lives in cloud_adapter.py; run_model() in
__init__.py routes by the registry's type.

Wrapped with _envelope() so it always returns run_model()'s standard shape and never
raises — same never-crash discipline as cloud_adapter.py.
"""
import json

from . import llm_client
from ._helpers import envelope as _envelope, require_keys
from .tripwire import tripwire

VALID_SEVERITIES = ("normal", "mild", "emergency")

# small local models use looser words; map them onto the contract's three levels
_SEVERITY_SYNONYMS = {
    "normal": "normal", "ok": "normal", "stable": "normal", "fine": "normal",
    "low": "normal", "routine": "normal", "green": "normal",
    "mild": "mild", "moderate": "mild", "warning": "mild", "caution": "mild",
    "concern": "mild", "medium": "mild", "amber": "mild", "yellow": "mild",
    "emergency": "emergency", "critical": "emergency", "severe": "emergency",
    "urgent": "emergency", "high": "emergency", "red": "emergency",
}

TRIAGE_SYSTEM = ("You are a careful clinical triage assistant for a rural night ward. "
                 "You cross-reference a fresh sensor reading against the patient's record. "
                 "Respond with JSON only.")


def build_triage_prompt(payload: dict) -> str:
    """Shared by the local path here and cloud_adapter's GPT path — keep them identical."""
    profile = payload.get("profile") or {}
    vitals = payload.get("vitals") or {}
    patient_id = payload.get("patient_id") or profile.get("patient_id", "unknown")
    return (
        f"PATIENT RECORD for {patient_id} (history, conditions, baseline vitals):\n"
        f"{json.dumps(profile, ensure_ascii=False)}\n\n"
        f"CURRENT SENSOR READING:\n{json.dumps(vitals)}\n\n"
        "Cross-reference the reading against this patient's baseline and history. "
        "Respond with ONLY a JSON object, no markdown fences, exactly this shape:\n"
        '{"severity": "normal" | "mild" | "emergency", "transcript": "..."}\n'
        "severity meanings: emergency = life-threatening right now; mild = needs "
        "medication or attention tonight; normal = within the expected range FOR THIS "
        "PATIENT (their baseline may differ from textbook values).\n"
        "transcript: a detailed clinical note of 5-8 sentences covering: what the reading "
        "shows, how it compares to this patient's baseline and history, the most likely "
        "cause, exactly what the nurse should do right now, and what to monitor next with "
        "concrete thresholds."
    )


def normalize_severity(value):
    if not isinstance(value, str):
        return None
    return _SEVERITY_SYNONYMS.get(value.strip().lower())


def _triage_impl(payload: dict) -> dict:
    """
    payload: {"patient_id": str, "vitals": {...}, "profile": {...}}
    """
    require_keys(payload, ["vitals"])
    vitals = payload.get("vitals") or {}
    profile = payload.get("profile") or {}
    patient_id = payload.get("patient_id") or profile.get("patient_id", "unknown")

    r = llm_client.route_chat(
        prompt=build_triage_prompt(payload),
        task="triage",
        device=payload["_device"],
        system=TRIAGE_SYSTEM,
    )
    if not r["ok"]:
        raise RuntimeError(r["error"])

    parsed = llm_client._try_parse_json(r["content"])
    parsed = parsed if isinstance(parsed, dict) else {}
    severity = normalize_severity(parsed.get("severity"))
    transcript = parsed.get("transcript")
    transcript = transcript.strip() if isinstance(transcript, str) else ""

    if severity is None or not transcript:
        # model wandered off-format: take severity from the hard tripwire (never miss an
        # unambiguous emergency), default the grey zone to mild, keep the raw text as note
        trip_sev, trip_reasons = tripwire(vitals)
        if severity is None:
            severity = trip_sev if trip_sev == "emergency" else "mild"
        if not transcript:
            transcript = str(r["content"]).strip()
            if trip_reasons:
                transcript = f"[tripwire: {'; '.join(trip_reasons)}] {transcript}"

    return {"op": "triage", "patient_id": patient_id, "severity": severity,
            "transcript": transcript}


triage = _envelope(_triage_impl)
