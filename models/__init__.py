"""
models/__init__.py

Public integration surface for the models package. The ONLY function other
teammates' code (the runtime agent) should ever call is run_model(op, payload).

v2 routing: the registry entry's `type` decides the path —
  * "cloud" -> cloud_adapter.call_cloud() (GPT). A cloud failure is RETURNED as an
    error envelope, never silently retried locally: the engine's ladder decides
    where the task goes next (that's the whole demo).
  * anything else -> the local op in ops.py via the configured adapter.
"""

from .execution_logger import logger

from . import cloud_adapter
from . import ops
import time
from datetime import datetime
from .registry import get_model_config
from .tripwire import tripwire  # re-exported: the watchdog's hard safety floor

_DISPATCH = {
    "triage": ops.triage,
}


def run_model(op: str, payload: dict, device: str = "surface", force_local: bool = False) -> dict:
    """
    Single public entry point for every op.

    device: registry key ("surface") or contract device_id ("pc-01") — aliases resolve.
    force_local: run the local path even for cloud-typed entries (benchmark use).
    """
    config = get_model_config(device, op)

    start_perf = time.perf_counter()
    started_at = datetime.now().isoformat()

    payload = payload.copy()
    payload["_device"] = device

    if config.get("type") == "cloud" and not force_local:
        result = cloud_adapter.call_cloud(op, payload)
    else:
        fn = _DISPATCH.get(op)
        if fn is None:
            raise ValueError(f"Unknown op: {op}")
        result = fn(payload)

    completed_at = datetime.now().isoformat()
    execution_time_ms = round(
        (time.perf_counter() - start_perf) * 1000,
        2
    )

    result.update({
        "task": op,
        "device": device,
        "model": config["model"],
        "adapter": config["adapter"],
        "started_at": started_at,
        "completed_at": completed_at,
        "execution_time_ms": execution_time_ms
    })

    logger.log(result.copy())

    return result
