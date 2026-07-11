"""Hardcoded planner: turn a request into the frozen 5-task health-report DAG.

This is deliberately NOT a general planner (build-plan §3). It expands DEMO_DAG from the
frozen contracts into concrete, per-request task dicts the orchestrator can dispatch:

    t1 extract_text -> (t2 summarize || t3 flag_risk) -> t4 patient_explainer
    t3 flag_risk -> t5 population_stats  (public -> cloud-eligible)
"""
from contracts.topics import DEMO_DAG, PRIORITY_NORMAL

DEFAULT_DEADLINE_MS = 8000


def plan_request(request_id: str, deadline_ms: int = DEFAULT_DEADLINE_MS) -> list:
    tasks = []
    for local_id, spec in DEMO_DAG.items():
        tasks.append({
            "task_id": f"{request_id}-{local_id}",
            "local_id": local_id,
            "request_id": request_id,
            "op": spec["op"],
            "depends_on": [f"{request_id}-{d}" for d in spec["depends_on"]],
            "privacy": spec["privacy"],
            "deadline_ms": deadline_ms,
            "priority": PRIORITY_NORMAL,
        })
    return tasks
