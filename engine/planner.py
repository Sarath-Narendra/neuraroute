"""Planner v2: every request (= one vitals reading) is exactly ONE triage task.

The 5-task PDF DAG is gone. A reading arrives -> one `triage` task is dispatched to
the best alive tier; the tier cross-references the patient's record and returns
{patient_id, severity, transcript}.
"""
from contracts.topics import OP_TRIAGE, PRIORITY_NORMAL, PRIVACY_PUBLIC

# Real local SLMs can take 15-30 s on a JSON-shaped prompt; the 3 s stale-detection is
# what catches dead tiers fast — this deadline only catches a hung-but-heartbeating one.
DEFAULT_DEADLINE_MS = 45000


def plan_request(request_id: str, deadline_ms: int = DEFAULT_DEADLINE_MS) -> list:
    return [{
        "task_id": f"{request_id}-t1",
        "local_id": "t1",
        "request_id": request_id,
        "op": OP_TRIAGE,
        "depends_on": [],
        "privacy": PRIVACY_PUBLIC,      # cloud-first by design: GPT is the preferred tier
        "deadline_ms": deadline_ms,
        "priority": PRIORITY_NORMAL,
    }]
