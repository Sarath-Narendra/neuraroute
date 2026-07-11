"""
models/ops.py

The DAG operations owned by models/: t1 extract_text, t2 summarize,
t3 flag_risk, t4 patient_explainer, and the LOCAL path for t5
population_stats (the cloud path lives in cloud_adapter.py; run_model() in
__init__.py decides which one to use for t5).

Every op is wrapped with _envelope() so it always returns run_model()'s
standard shape and never raises — same never-crash discipline as
cloud_adapter.py, applied to the local side too.
"""

from . import llm_client
from ._helpers import envelope as _envelope, require_keys


# ---------------------------------------------------------------------------
# t1 - extract_text (PyMuPDF, no LLM — deterministic, no prompt needed)
# ---------------------------------------------------------------------------

def _extract_text_impl(payload: dict) -> dict:
    """
    payload: {"pdf_path": <str>} OR {"pdf_bytes_b64": <str>}
    """
    if "pdf_path" not in payload and "pdf_bytes_b64" not in payload:
        raise ValueError("payload must contain 'pdf_path' or 'pdf_bytes_b64'")

    import fitz  # PyMuPDF — pip install pymupdf
    import base64

    if "pdf_path" in payload:
        doc = fitz.open(payload["pdf_path"])
    else:
        raw = base64.b64decode(payload["pdf_bytes_b64"])
        doc = fitz.open(stream=raw, filetype="pdf")

    text_parts = [page.get_text() for page in doc]
    page_count = len(text_parts)
    doc.close()

    return {
        "op": "extract_text",
        "text": "\n".join(text_parts).strip(),
        "page_count": page_count,
    }


extract_text = _envelope(_extract_text_impl)


# ---------------------------------------------------------------------------
# t2 - summarize
# ---------------------------------------------------------------------------

def _summarize_impl(payload: dict) -> dict:
    require_keys(payload, ["text"])
    text = payload["text"]
    prompt = (
        "Summarize the following health document in 3-4 sentences, plain "
        f"language, no jargon:\n\n{text}"
    )
    r = llm_client.route_chat(
        prompt=prompt,
        task="summarize",
        device=payload["_device"],
        system="You are a concise medical document summarizer."
    )
    if not r["ok"]:
        raise RuntimeError(r["error"])
    return {"op": "summarize", "summary": r["content"]}


summarize = _envelope(_summarize_impl)


# ---------------------------------------------------------------------------
# t3 - flag_risk
# ---------------------------------------------------------------------------

def _flag_risk_impl(payload: dict) -> dict:
    require_keys(payload, ["text"])
    text = payload["text"]
    prompt = (
        "Read the following health document and list any risk factors or "
        "concerning findings as a JSON array of short strings. Respond "
        f"with JSON only, no other text:\n\n{text}"
    )
    r = llm_client.route_chat(
        prompt=prompt,
        task="flag_risk",
        device=payload["_device"],
        system="You are a clinical risk-flagging assistant. Respond with JSON only."
    )
    if not r["ok"]:
        raise RuntimeError(r["error"])
    parsed = llm_client._try_parse_json(r["content"])

    if parsed is None:
        parsed = {"text": r["content"]}

    content = parsed
    if isinstance(content, list):
        risks = content
    elif isinstance(content, dict):
        risks = content.get("risks", content.get("text", []))
    else:
        risks = []
    return {
        "op": "flag_risk",
        "risks": risks
    }

flag_risk = _envelope(_flag_risk_impl)


# ---------------------------------------------------------------------------
# t4 - patient_explainer
# ---------------------------------------------------------------------------

def _patient_explainer_impl(payload: dict) -> dict:
    require_keys(payload, ["risks"])
    risks = payload["risks"]
    prompt = (
        "Explain the following health risk findings to a patient in "
        "simple, reassuring, plain language (max 5 sentences). Do not "
        f"diagnose, only explain what was flagged: {risks}"
    )
    r = llm_client.route_chat(
        prompt=prompt,
        task="patient_explainer",
        device=payload["_device"],
        system="You are a compassionate patient-facing health explainer."
    )
    if not r["ok"]:
        raise RuntimeError(r["error"])
    return {"op": "patient_explainer", "explanation": r["content"]}


patient_explainer = _envelope(_patient_explainer_impl)


# ---------------------------------------------------------------------------
# t5 - population_stats, LOCAL path only.
# The cloud path lives in cloud_adapter.call_cloud("population_stats", ...).
# run_model() in __init__.py decides which one to use.
# ---------------------------------------------------------------------------

def _population_stats_local_impl(payload: dict) -> dict:
    require_keys(payload, ["risks"])
    risks = payload["risks"]
    prompt = (
        "Given these risk records, compute summary population statistics. "
        "Respond with ONLY a valid JSON object with keys 'summary' and "
        "'stats' (stats should include count, mean_risk, high_risk_pct). "
        "Rules: no markdown code fences, no comments, no trailing commas, "
        "all keys and strings double-quoted, no text before or after the "
        f"JSON object. Risk records: {risks}"
    )
    r = llm_client.route_chat(
        prompt=prompt,
        task="population_stats",
        device=payload["_device"],
        system="You are a population health statistics assistant. Respond with JSON only."
    )
    if not r["ok"]:
        raise RuntimeError(r["error"])
    parsed = llm_client._try_parse_json(r["content"])

    if parsed is None:
        parsed = {"summary": r["content"]}
    content = parsed
    content.setdefault("op", "population_stats")
    content.setdefault("stats", {})
    return content


population_stats_local = _envelope(_population_stats_local_impl)