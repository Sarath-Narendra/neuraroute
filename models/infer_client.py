"""
models/infer_client.py

Bridge to the standalone AI-inference servers (Eswar's module): each device exposes
`POST /infer` with `{"patient": "<free text>"}` and returns a fixed schema. This client
renders NeuraRoute's structured triage payload into that free-text description, calls the
server, and maps its response back into NeuraRoute's `{patient_id, severity, transcript}`.

His schema is frozen and owned by him — the mapping lives entirely on our side, so his
servers change models freely without touching the engine. Never raises: a failed /infer
(server down, no internet for the Groq cloud server, bad shape) comes back as an error
envelope so the engine fails the task over DOWN THE LADDER — that's the whole demo.

His response shape (models change, this schema doesn't):
    {"device","runtime","model",
     "response": {"summary","symptoms":[],"possible_conditions":[],
                  "severity","emergency":bool,"confidence","next_action","requires_cloud":bool}}
"""
import time

from .ops import normalize_severity

DEFAULT_TIMEOUT_S = 60.0   # GenieX/on-device can be slow; the ladder's stale timer catches dead servers faster


def _describe(payload: dict) -> str:
    """Render {patient_id, vitals, profile} into the clinical free-text his /infer expects."""
    profile = payload.get("profile") or {}
    vitals = payload.get("vitals") or {}
    pid = payload.get("patient_id") or profile.get("patient_id", "unknown")
    name = profile.get("name", pid)
    bits = [f"Patient {name} ({pid})"]
    if profile.get("age"):
        bits.append(f"{profile['age']} years old")
    if profile.get("conditions"):
        bits.append("known conditions: " + ", ".join(profile["conditions"]))
    if profile.get("history_summary"):
        bits.append("history: " + profile["history_summary"])
    if profile.get("baseline"):
        base = ", ".join(f"{k} {v}" for k, v in profile["baseline"].items())
        bits.append(f"baseline vitals: {base}")
    if vitals:
        cur = ", ".join(f"{k} {v}" for k, v in vitals.items())
        bits.append(f"CURRENT sensor reading: {cur}")
    return ". ".join(bits) + "."


def _map_severity(resp: dict) -> str:
    """His {severity, emergency} -> our normal|mild|emergency."""
    if resp.get("emergency") is True:
        return "emergency"
    sev = normalize_severity(resp.get("severity"))
    if sev:
        return sev
    # unmapped severity string with emergency=false: treat any non-empty flag as mild, else normal
    return "mild" if resp.get("severity") else "normal"


def _map_transcript(resp: dict) -> str:
    """Fold his richer fields into one readable transcript (the phone shows this)."""
    parts = []
    if resp.get("summary"):
        parts.append(str(resp["summary"]).strip())
    conds = resp.get("possible_conditions") or []
    if conds:
        parts.append("Possible: " + ", ".join(str(c) for c in conds) + ".")
    if resp.get("next_action"):
        parts.append("Next: " + str(resp["next_action"]).strip())
    return " ".join(parts).strip() or "No detail returned by the inference server."


def call_infer(url: str, payload: dict, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
    """POST to a device's /infer and return run_model's standard envelope. Never raises."""
    start = time.time()
    try:
        import requests
    except ImportError as e:
        return _error(f"requests not installed: {e}", start)

    profile = payload.get("profile") or {}
    patient_id = payload.get("patient_id") or profile.get("patient_id", "unknown")
    try:
        r = requests.post(url, json={"patient": _describe(payload)}, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.Timeout:
        return _error(f"/infer timeout at {url}", start)
    except requests.exceptions.RequestException as e:
        return _error(f"/infer unreachable at {url}: {e}", start)   # e.g. Groq cloud with no internet
    except ValueError as e:
        return _error(f"/infer bad JSON from {url}: {e}", start)

    resp = data.get("response") if isinstance(data, dict) else None
    if not isinstance(resp, dict):
        return _error(f"/infer response missing 'response' object: {data!r:.200}", start)

    result = {
        "op": "triage",
        "patient_id": patient_id,
        "severity": _map_severity(resp),
        "transcript": _map_transcript(resp),
        # carry a few of his signals through for the engine (ladder/watchdog can use them)
        "confidence": resp.get("confidence"),
        "requires_cloud": resp.get("requires_cloud"),
        "backend": {"device": data.get("device"), "runtime": data.get("runtime"),
                    "model": data.get("model")},
    }
    return {"status": "ok", "result": result,
            "latency_ms": int((time.time() - start) * 1000),
            "cloud_call": False, "mock": False}


def _error(msg: str, start: float) -> dict:
    return {"status": "error", "result": None, "error": msg,
            "latency_ms": int((time.time() - start) * 1000), "cloud_call": False, "mock": False}
