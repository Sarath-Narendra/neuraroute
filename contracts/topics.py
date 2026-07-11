"""Frozen v1 constants shared by every NeuraRoute component.

Owned by Sarath. This is the single source of truth for MQTT topic strings, op names,
enums, and the hardcoded demo DAG. Import from here — never hardcode a topic string in
your own file, or integration will drift. Any change needs a version bump + group sign-off.
"""
import os

CONTRACTS_VERSION = "1.1.0"   # 1.1.0: removed heartbeat temperature_c (unused — Gowtham, 2026-07)

# --- MQTT topics (frozen) ---
TOPIC_HEARTBEAT = "neuraroute/heartbeat"          # device -> engine, every ~1.5 s
TOPIC_EVENT = "neuraroute/event"                  # engine -> dashboard (decisions/failover/metrics)
TOPIC_ADMIN = "neuraroute/admin"                  # demo controls (simulate_battery_critical, reset)
TOPIC_TASK_WILDCARD = "neuraroute/task/+"         # engine -> device (subscribe side)
TOPIC_RESULT_WILDCARD = "neuraroute/result/+"     # device -> engine (subscribe side)


def topic_task(device_id: str) -> str:
    """engine -> a specific device."""
    return f"neuraroute/task/{device_id}"


def topic_result(task_id: str) -> str:
    """device -> engine, for a specific task."""
    return f"neuraroute/result/{task_id}"


# --- ops: the 5-task health-report DAG (models dev implements run_model for each) ---
OP_EXTRACT_TEXT = "extract_text"
OP_SUMMARIZE = "summarize"
OP_FLAG_RISK = "flag_risk"
OP_PATIENT_EXPLAINER = "patient_explainer"
OP_POPULATION_STATS = "population_stats"
OP_ECHO = "echo"  # trivial op for round-trip plumbing tests
OPS = [OP_EXTRACT_TEXT, OP_SUMMARIZE, OP_FLAG_RISK, OP_PATIENT_EXPLAINER, OP_POPULATION_STATS]

# --- enums ---
PRIVACY_SENSITIVE = "sensitive"   # must run on a device with privacy_ok=true (never cloud)
PRIVACY_PUBLIC = "public"         # cloud-eligible

PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"            # SOS / preemptive

RESULT_OK = "ok"
RESULT_ERROR = "error"
RESULT_TIMEOUT = "timeout"

# --- event types (event.schema.json "type") ---
EV_DEVICE_ALIVE = "device_alive"
EV_DEVICE_STALE = "device_stale"
EV_REQUEST_START = "request_start"
EV_PLACEMENT = "placement"
EV_TASK_START = "task_start"
EV_TASK_DONE = "task_done"
EV_FAILOVER = "failover"
EV_METRICS = "metrics"
EV_REQUEST_DONE = "request_done"
EV_POLICY = "policy"
EV_SOS = "sos"

# --- timing (frozen) ---
STALE_TIMEOUT_S = 3.0        # no heartbeat for this long -> device quarantined
HEARTBEAT_INTERVAL_S = 1.5   # device heartbeat cadence

# --- broker (one env var is how "combine at a single space" happens at the venue) ---
BROKER_PORT = 1883


def broker_host() -> str:
    return os.environ.get("NEURAROUTE_BROKER", "localhost")


# --- the hardcoded demo DAG (do NOT build a general planner; the engine plans exactly this) ---
# t1 extract_text -> (t2 summarize || t3 flag_risk) -> t4 patient_explainer ; t3 -> t5 population_stats
DEMO_DAG = {
    "t1": {"op": OP_EXTRACT_TEXT,       "depends_on": [],            "privacy": PRIVACY_SENSITIVE},
    "t2": {"op": OP_SUMMARIZE,          "depends_on": ["t1"],        "privacy": PRIVACY_SENSITIVE},
    "t3": {"op": OP_FLAG_RISK,          "depends_on": ["t1"],        "privacy": PRIVACY_SENSITIVE},
    "t4": {"op": OP_PATIENT_EXPLAINER,  "depends_on": ["t2", "t3"],  "privacy": PRIVACY_SENSITIVE},
    "t5": {"op": OP_POPULATION_STATS,   "depends_on": ["t3"],        "privacy": PRIVACY_PUBLIC},
}
