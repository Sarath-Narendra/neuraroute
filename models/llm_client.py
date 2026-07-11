"""
models/llm_client.py

OpenAI-compatible client for the LOCAL small LLM (LM Studio ARM64 server on
the Surface, plan A per build plan §8; llama.cpp CPU is the fallback, but
both expose the same OpenAI-compatible API so this file doesn't change
between them). Used by ops t2-t4 (summarize, flag_risk, patient_explainer)
and by population_stats' local/force_local path.

Deliberately separate from cloud_adapter.py: same wire protocol (OpenAI-
compatible chat completions), but a different base URL/model and a
different failure domain — "local server not running" vs "network/cloud
unreachable" are different problems even though the request shape matches.

Env vars:
    NEURAROUTE_LOCAL_BASE_URL  - default http://localhost:1234/v1 (LM Studio default)
    NEURAROUTE_LOCAL_MODEL     - default "local-model" (LM Studio's generic
                                  alias; set to your loaded model's name if
                                  your server requires an exact match)
"""

import os
import json
from .registry import get_model_config

NEURAROUTE_LOCAL_BASE_URL = os.environ.get("NEURAROUTE_LOCAL_BASE_URL", "http://localhost:1234/v1")
NEURAROUTE_LOCAL_MODEL = os.environ.get("NEURAROUTE_LOCAL_MODEL", "local-model")
# Small local models on CPU can genuinely take 15-30s+ per call for
# JSON-shaped prompts (observed: 12-32s on a real Phi-3 test run). 30s was
# too tight and produced a real timeout in testing — 60s by default, still
# overridable per-call or via env var.
DEFAULT_TIMEOUT_S = float(os.environ.get("NEURAROUTE_LOCAL_TIMEOUT_S", "60.0"))


def chat(prompt: str, system: str = None, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
    """
    Send one chat-completion request to the local LLM server.

    Returns:
        {"ok": True, "content": <str>}   on success
        {"ok": False, "error": <str>}    on failure

    Never raises — callers (ops.py) turn a failed result into the standard
    run_model() error shape.
    """
    try:
        import requests
    except ImportError as e:
        return {"ok": False, "error": f"requests not installed: {e}"}

    url = NEURAROUTE_LOCAL_BASE_URL.rstrip("/") + "/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {
        "model": NEURAROUTE_LOCAL_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        resp = requests.post(url, json=body, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {"ok": True, "content": content}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": str(e)}
    except (KeyError, IndexError, ValueError) as e:
        return {"ok": False, "error": f"malformed response: {e}"}

def route_chat(
    prompt: str,
    task: str,
    device: str = "surface",
    system: str = None,
    timeout_s: float = DEFAULT_TIMEOUT_S
):
    """
    Route a chat request to the correct inference backend based on
    the model registry.
    """

    config = get_model_config(device, task)
    adapter = config["adapter"]

    if adapter == "llm_client":
        return chat(
            prompt=prompt,
            system=system,
            timeout_s=timeout_s
        )

    elif adapter == "executorch":
        return executorch_chat(
            prompt=prompt,
            model=config["model"],
            system=system,
            timeout_s=timeout_s
        )

    elif adapter == "gemma":
        return gemma_chat(
            prompt=prompt,
            system=system,
            timeout_s=timeout_s
        )

    return {
        "ok": False,
        "error": f"Unknown adapter: {adapter}"
    }

def chat_json(prompt: str, system: str = None, timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
    """
    Like chat(), but attempts to parse the model's reply as JSON. Small local
    models routinely wrap JSON in markdown code fences (```json ... ```) or
    slip in a // comment, both of which break plain json.loads(). This tries
    a few tolerant extraction passes before giving up and wrapping the raw
    text — confirmed against real Phi-3 output that did exactly this.
    """
    result = chat(prompt, system=system, timeout_s=timeout_s)
    if not result["ok"]:
        return result

    parsed = _try_parse_json(result["content"])
    if parsed is not None:
        return {"ok": True, "content": parsed}

    return {"ok": True, "content": {"text": result["content"]}}


def _try_parse_json(raw: str):
    """
    Attempt increasingly tolerant parses of a model's JSON-ish output.
    Small local models produce a range of near-JSON: markdown fences, //
    comments, unquoted keys, single-quoted strings, trailing commas, and
    even truncated/unbalanced braces. This tries each repair independently
    and in combination. Returns the parsed object, or None if nothing
    worked.
    """
    import re

    candidates = [raw]

    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1))

    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0))
    # If fenced content itself has no closing brace (truncated output), take
    # everything from the first '{' onward instead of requiring a match.
    if fenced:
        open_brace = fenced.group(1).find("{")
        if open_brace != -1:
            candidates.append(fenced.group(1)[open_brace:])

    for candidate in candidates:
        text = candidate.strip()
        if not text:
            continue
        for repaired in _repair_passes(text):
            try:
                return json.loads(repaired)
            except (json.JSONDecodeError, TypeError):
                continue

    return None


def _repair_passes(text: str):
    """
    Yield progressively more aggressive repaired versions of `text` to try
    parsing as JSON. Each repair is applied on top of the last.
    """
    import re

    yield text

    # Strip // line comments (invalid in JSON but common in model output).
    no_comments = re.sub(r"//[^\n\"]*(?=\n|$)", "", text)
    yield no_comments

    # Quote bare object keys, e.g. `endpoints: [...]` -> `"endpoints": [...]`
    bare_keys_quoted = re.sub(
        r'(?<=[{,\s])([A-Za-z_][A-Za-z0-9_]*)\s*:', r'"\1":', no_comments
    )
    yield bare_keys_quoted

    # Convert simple single-quoted strings to double-quoted.
    single_to_double = re.sub(r"'([^'\"]*)'", r'"\1"', bare_keys_quoted)
    yield single_to_double

    # Remove trailing commas before a closing brace/bracket.
    no_trailing_commas = re.sub(r",\s*([}\]])", r"\1", single_to_double)
    yield no_trailing_commas

    # Last resort: balance unclosed braces/brackets (handles truncated
    # output) by appending whatever closers are still owed.
    yield _balance_brackets(no_trailing_commas)


def _balance_brackets(text: str) -> str:
    """
    Append closing braces/brackets for any that were opened but never
    closed — a common symptom of a model's output getting cut off or
    tangled mid-structure. Ignores brace-like characters inside string
    literals so it doesn't get fooled by quoted content.
    """
    pairs = {"{": "}", "[": "]"}
    closers = {"}": "{", "]": "["}
    stack = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in pairs:
            stack.append(ch)
        elif ch in closers and stack and stack[-1] == closers[ch]:
            stack.pop()

    return text + "".join(pairs[ch] for ch in reversed(stack))

def executorch_chat(
    prompt,
    model,
    system=None,
    timeout_s=DEFAULT_TIMEOUT_S
):
    """
    Placeholder for Qualcomm ExecuTorch backend.
    """
    raise NotImplementedError(
        "ExecuTorch backend not implemented yet."
    )


def gemma_chat(
    prompt,
    system=None,
    timeout_s=DEFAULT_TIMEOUT_S
):
    """
    Placeholder for Qualcomm Gemma backend.
    """
    raise NotImplementedError(
        "Gemma backend not implemented yet."
    )