"""
models/__init__.py

Public integration surface for the models package. The ONLY function other
teammates' code (the runtime agent) should ever call is run_model(op,
payload). It never exposes a separate cloud code path — population_stats
internally decides whether to go local or delegate to cloud_adapter.
"""

from .execution_logger import logger

from . import cloud_adapter
from . import ops
import time
from datetime import datetime
from .registry import get_model_config

_DISPATCH = {
    "extract_text": ops.extract_text,
    "summarize": ops.summarize,
    "flag_risk": ops.flag_risk,
    "patient_explainer": ops.patient_explainer,
}


def run_model(op: str, payload: dict, device: str = "surface", force_local: bool = False) -> dict:
    """
    Single public entry point for every op in the DAG.

    force_local: when True, always use the local path even for ops that are
                 normally cloud-eligible. Used by the benchmark script
                 (metrics/run_bench.py) to run a fully-local baseline pass.
                 Has no effect on ops other than population_stats, since
                 those never had a cloud path to begin with.
    """
    if op == "population_stats":
        return _run_population_stats(
            payload,
            device=device,
            force_local=force_local
        )

    fn = _DISPATCH.get(op)
    if fn is None:
        raise ValueError(f"Unknown op: {op}")
    config = get_model_config(device, op)

    start_perf = time.perf_counter()
    started_at = datetime.now().isoformat()

    payload = payload.copy()
    payload["_device"] = device

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


def _run_population_stats(
    payload: dict,
    device: str = "cloud",
    force_local: bool = False
) -> dict:
    """
    population_stats is the one op marked sensitive: false in the DAG, so
    it's eligible for cloud escalation.
    """

    config = get_model_config("cloud", "population_stats")

    start_perf = time.perf_counter()
    started_at = datetime.now().isoformat()

    if force_local:
        result = ops.population_stats_local(payload)

    else:
        cloud_result = cloud_adapter.call_cloud(
            "population_stats",
            payload
        )

        if cloud_result["status"] == "error":
            result = ops.population_stats_local(payload)
            result["cloud_fallback"] = True
            result["cloud_error"] = cloud_result.get("error")
        else:
            result = cloud_result

    completed_at = datetime.now().isoformat()
    execution_time_ms = round(
        (time.perf_counter() - start_perf) * 1000,
        2
    )

    result.update({
        "task": "population_stats",
        "device": device,
        "model": config["model"],
        "adapter": config["adapter"],
        "started_at": started_at,
        "completed_at": completed_at,
        "execution_time_ms": execution_time_ms
    })
    logger.log(result.copy())
    return result