"""
models/_helpers.py

Small shared utilities used across the models package. Kept deliberately
thin — this is not a dumping ground, just the handful of things that would
otherwise be copy-pasted between ops.py and cloud_adapter.py.
"""

import time


def envelope(fn):
    """
    Wrap an op implementation so it always returns run_model()'s standard
    shape and never raises:
        {
            "status": "ok" | "error",
            "result": <dict> | None,
            "latency_ms": <int>,
            "cloud_call": False,
            "mock": False,
            "error": <str>,   # only present on error
        }

    Used by ops.py for the local ops (t1-t5 local path). cloud_adapter.py
    does NOT use this — its shape has extra fields (cloud_call/mock are
    meaningful there, not just always-False) and its own error paths for
    network-specific failures, so it keeps its own wrapping logic.
    """
    def wrapped(payload):
        start = time.time()
        try:
            result = fn(payload)
            return {
                "status": "ok",
                "result": result,
                "latency_ms": elapsed_ms(start),
                "cloud_call": False,
                "mock": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "result": None,
                "error": str(e),
                "latency_ms": elapsed_ms(start),
                "cloud_call": False,
                "mock": False,
            }
    return wrapped


def elapsed_ms(start: float) -> int:
    """Milliseconds elapsed since `start` (a time.time() value)."""
    return int((time.time() - start) * 1000)


def require_keys(payload: dict, keys: list) -> None:
    """
    Raise a clear ValueError if any required key is missing from payload.
    Ops call this first so a bad/missing field fails with a readable
    message instead of a confusing KeyError deep inside a prompt string.
    """
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ValueError(f"payload missing required key(s): {', '.join(missing)}")