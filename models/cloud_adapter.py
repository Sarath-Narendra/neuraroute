"""
models/cloud_adapter.py

Internal cloud-escalation adapter for NeuraRoute.

Public integration contract for the rest of the team is run_model() (in this
package's __init__ / ops layer) — NOT anything in this file. The functions
here (call_cloud, get_call_count, reset_call_count) are internal, but are
importable directly by tests and the benchmark script (App 3).

Wire protocol: OpenAI-compatible chat-completions request. This targets
Qualcomm AI Inference Suite (AI Cloud 100) at the venue, which exposes an
OpenAI-compatible API; any OpenAI-compatible endpoint (LM Studio, a hosted
compat endpoint, etc.) works as a stand-in until then.

Mock mode is ON by default. This is a deliberate safety default: if you
forget to flip it, the demo just runs on canned data instead of dying to
venue wifi. Mock responses are delayed ~2s to keep demo/benchmark latency
numbers looking like a real cloud round-trip.

Env vars:
    NEURAROUTE_CLOUD_BASE_URL   - OpenAI-compatible base URL (e.g. https://.../v1)
    NEURAROUTE_CLOUD_API_KEY    - API key / bearer token
    NEURAROUTE_CLOUD_MODEL      - model name to request
    NEURAROUTE_CLOUD_MOCK       - "true"/"false", default "true"
"""

import os
import time
import json

from .ops import TRIAGE_SYSTEM, build_triage_prompt, normalize_severity
from .tripwire import tripwire

# ---------------------------------------------------------------------------
# Config (kept inline and small on purpose — this is the one place to look
# when flipping mock on/off at the venue)
# ---------------------------------------------------------------------------

NEURAROUTE_CLOUD_BASE_URL = os.environ.get("NEURAROUTE_CLOUD_BASE_URL", "")
NEURAROUTE_CLOUD_API_KEY = os.environ.get("NEURAROUTE_CLOUD_API_KEY", "")
NEURAROUTE_CLOUD_MODEL = os.environ.get("NEURAROUTE_CLOUD_MODEL", "gpt-4o-mini")
MOCK_MODE = os.environ.get("NEURAROUTE_CLOUD_MOCK", "true").lower() == "true"

# GPT with a detailed transcript typically answers in 3-8 s; a hard timeout here is
# what turns "internet died mid-call" into a clean ladder failover instead of a hang.
DEFAULT_TIMEOUT_S = float(os.environ.get("NEURAROUTE_CLOUD_TIMEOUT_S", "15.0"))
MOCK_DELAY_S = 2.0  # keeps demo latency numbers looking like a real cloud round-trip

# ---------------------------------------------------------------------------
# Call counter (for App 3 cost metrics: cloud cost = call count x price)
# ---------------------------------------------------------------------------

_call_count = 0


def get_call_count() -> int:
    """Return the number of call_cloud() invocations since the last reset."""
    return _call_count


def reset_call_count() -> None:
    """Reset the call counter. Use between baseline and orchestrated runs."""
    global _call_count
    _call_count = 0


# ---------------------------------------------------------------------------
# Public-ish entry point (internal to models/, called by run_model())
# ---------------------------------------------------------------------------

def call_cloud(op: str, payload: dict, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
    """
    Escalate one operation to the cloud.

    op: the operation being escalated (in practice, always "population_stats" —
        the only task marked sensitive: false in the DAG).
    payload: same shape run_model() would receive for that op.

    Returns a dict, ALWAYS in this shape:
        {
            "status": "ok" | "error",
            "result": <output, same shape run_model() would produce>,
            "latency_ms": <int>,
            "cloud_call": true,
            "mock": true | false,
            "error": <str, only present if status == "error">
        }

    Never raises. Timeouts and network errors are caught and returned in the
    standard shape so the scheduler / demo never crashes on a bad connection.
    """
    global _call_count
    _call_count += 1

    start = time.time()

    if MOCK_MODE:
        return _mock_call(op, payload, start)

    return _real_call(op, payload, timeout_s, start)


# ---------------------------------------------------------------------------
# Mock path
# ---------------------------------------------------------------------------

def _mock_call(op: str, payload: dict, start: float) -> dict:
    time.sleep(MOCK_DELAY_S)
    return {
        "status": "ok",
        "result": _fake_result_for(op, payload),
        "latency_ms": int((time.time() - start) * 1000),
        "cloud_call": True,
        "mock": True,
    }


def _fake_result_for(op: str, payload: dict) -> dict:
    """
    Plausible canned result for mock mode. Keep this in sync with the real shape
    triage produces (models/ops.py) so downstream code can't tell the difference
    structurally. The mock severity comes from the same hard tripwire the watchdog
    uses plus a borderline check, so demo verdicts look clinically sane.
    """
    if op == "triage":
        vitals = payload.get("vitals") or {}
        profile = payload.get("profile") or {}
        patient_id = payload.get("patient_id") or profile.get("patient_id", "unknown")
        name = profile.get("name", patient_id)
        baseline = profile.get("baseline") or {}

        severity, reasons = tripwire(vitals)
        if severity != "emergency":
            borderline = []
            if float(vitals.get("spo2", 99) or 99) < 93:
                borderline.append("SpO2 trending low")
            if float(vitals.get("temp_c", 37) or 37) > 38.2:
                borderline.append("fever")
            if float(vitals.get("hr", 80) or 80) > 110:
                borderline.append("tachycardia")
            severity = "mild" if borderline else "normal"
            reasons = borderline

        deltas = []
        for k in ("hr", "spo2", "temp_c", "resp_rate"):
            if k in vitals and k in baseline:
                deltas.append(f"{k} {vitals[k]} (baseline {baseline[k]})")
        transcript = (
            f"[MOCK GPT] Cross-referenced {name}'s record ({', '.join(profile.get('conditions', []) or ['no known conditions'])}). "
            f"Current reading: {', '.join(deltas) or json.dumps(vitals)}. "
            + (f"Findings: {'; '.join(reasons)}. " if reasons else "All parameters within this patient's expected range. ")
            + {"emergency": "Immediate clinical attention required — alert the doctor now, prepare for escalation, and stay with the patient.",
               "mild": "Give charted medication, re-check vitals in 30 minutes, and escalate if the trend worsens.",
               "normal": "Continue routine monitoring on the next 20-second cycle; no action needed."}[severity]
        )
        return {"op": "triage", "patient_id": patient_id, "severity": severity,
                "transcript": transcript}

    # Generic fallback for any other op accidentally routed here
    return {
        "op": op,
        "summary": f"Mock cloud result for '{op}'.",
        "stats": {},
    }


# ---------------------------------------------------------------------------
# Real path — OpenAI-compatible chat completions
# ---------------------------------------------------------------------------

def _real_call(op: str, payload: dict, timeout_s: float, start: float) -> dict:
    try:
        import requests  # local import so mock mode never needs the dependency
    except ImportError as e:
        return _cloud_error(f"requests not installed: {e}", start)

    if not NEURAROUTE_CLOUD_BASE_URL:
        return _cloud_error("NEURAROUTE_CLOUD_BASE_URL not configured", start)

    prompt = _build_prompt(op, payload)
    url = NEURAROUTE_CLOUD_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if NEURAROUTE_CLOUD_API_KEY:
        headers["Authorization"] = f"Bearer {NEURAROUTE_CLOUD_API_KEY}"

    system = TRIAGE_SYSTEM if op == "triage" else \
        "You are a data analysis assistant. Respond with concise JSON only."
    body = {
        "model": NEURAROUTE_CLOUD_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
        result = _parse_chat_completion(op, data)
        if op == "triage":
            profile = payload.get("profile") or {}
            result.setdefault("patient_id",
                              payload.get("patient_id") or profile.get("patient_id", "unknown"))
        return {
            "status": "ok",
            "result": result,
            "latency_ms": int((time.time() - start) * 1000),
            "cloud_call": True,
            "mock": False,
        }
    except requests.exceptions.Timeout:
        return _cloud_error("timeout", start)
    except requests.exceptions.RequestException as e:
        return _cloud_error(str(e), start)
    except (ValueError, KeyError, IndexError) as e:
        # bad/unexpected response shape from the endpoint
        return _cloud_error(f"malformed response: {e}", start)


def _build_prompt(op: str, payload: dict) -> str:
    """
    Build the chat prompt for a given op. The triage prompt is shared with the
    local path (models/ops.py) so every tier answers the same question.
    """
    if op == "triage":
        return build_triage_prompt(payload)
    clean = {k: v for k, v in payload.items() if k != "_device"}
    return f"Perform operation '{op}' with payload: {json.dumps(clean)}"


def _parse_chat_completion(op: str, data: dict) -> dict:
    """
    Extract the assistant's message content from an OpenAI-compatible
    chat-completions response and return it in run_model()'s result shape.
    """
    content = data["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        # Endpoint didn't return clean JSON — wrap the raw text instead of
        # failing the whole call.
        parsed = {"transcript": content} if op == "triage" else {"summary": content, "stats": {}}
    if op == "triage":
        parsed["severity"] = normalize_severity(parsed.get("severity")) or "mild"
        if not isinstance(parsed.get("transcript"), str) or not parsed["transcript"].strip():
            parsed["transcript"] = str(content).strip()
    parsed.setdefault("op", op)
    return parsed


def _cloud_error(msg: str, start: float) -> dict:
    return {
        "status": "error",
        "result": None,
        "error": msg,
        "latency_ms": int((time.time() - start) * 1000),
        "cloud_call": True,
        "mock": False,
    }