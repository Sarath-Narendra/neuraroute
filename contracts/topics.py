"""Frozen v2 constants shared by every NeuraRoute component.

Owned by Sarath. This is the single source of truth for MQTT topic strings, op names,
enums, severity levels, and the connectivity ladder. Import from here — never hardcode
a topic string in your own file, or integration will drift. Any change needs a version
bump + group sign-off.

v2.0.0 (2026-07-11) — THE PIVOT: continuous vitals triage for a 10-patient night ward.
  * ONE op: triage (the 5-task PDF DAG is gone; DEMO_DAG deleted)
  * scheduling = fixed connectivity ladder (cloud -> pc -> phone -> arduino), first
    alive tier wins; the cost function + policy profiles are deleted
  * new topics: neuraroute/reading  (engine fans out every raw reading -> watchdog)
                neuraroute/sos      (arduino watchdog -> engine: extreme emergency)
  * heartbeats are liveness-only: no cpu/npu/battery telemetry
"""
import os

CONTRACTS_VERSION = "2.0.0"

# --- MQTT topics (frozen) ---
TOPIC_HEARTBEAT = "neuraroute/heartbeat"          # device -> engine, every ~1.5 s (liveness)
TOPIC_EVENT = "neuraroute/event"                  # engine -> UIs (placements/failover/sos/metrics)
TOPIC_ADMIN = "neuraroute/admin"                  # demo controls
TOPIC_TASK_WILDCARD = "neuraroute/task/+"         # engine -> device (subscribe side)
TOPIC_RESULT_WILDCARD = "neuraroute/result/+"     # device -> engine (subscribe side)
TOPIC_READING = "neuraroute/reading"              # engine -> all: every raw {patient_id, vitals}
TOPIC_SOS = "neuraroute/sos"                      # watchdog -> engine: extreme-emergency alert


def topic_task(device_id: str) -> str:
    """engine -> a specific device."""
    return f"neuraroute/task/{device_id}"


def topic_result(task_id: str) -> str:
    """device -> engine, for a specific task."""
    return f"neuraroute/result/{task_id}"


# --- ops: v2 has exactly one — triage a fresh vitals reading against the record ---
OP_TRIAGE = "triage"
OP_ECHO = "echo"  # trivial op for round-trip plumbing tests
OPS = [OP_TRIAGE]

# --- severity levels (triage output + sos events) ---
SEV_NORMAL = "normal"        # within expected range for this patient
SEV_MILD = "mild"            # needs medication / attention tonight
SEV_EMERGENCY = "emergency"  # life-threatening now -> doctor notified immediately
SEVERITIES = [SEV_NORMAL, SEV_MILD, SEV_EMERGENCY]

# --- the connectivity ladder: scheduler picks the FIRST alive tier, in this order ---
PRIORITY_LADDER = ["cloud-01", "pc-01", "phone-01", "arduino-01"]
TIER_LABELS = {
    "cloud-01": "GPT (cloud)",
    "pc-01": "PC (local LLM)",
    "phone-01": "Phone (local LLM)",
    "arduino-01": "Arduino (SLM)",
}

# --- enums ---
PRIVACY_SENSITIVE = "sensitive"   # kept for schema compat; v2 triage is cloud-first by design
PRIVACY_PUBLIC = "public"

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
EV_POLICY = "policy"   # vestigial in v2 (no cost profiles); kept so old payloads don't break parsers
EV_SOS = "sos"

# --- timing (frozen) ---
STALE_TIMEOUT_S = 3.0        # no heartbeat for this long -> device quarantined
HEARTBEAT_INTERVAL_S = 1.5   # device heartbeat cadence

# --- broker (one env var is how "combine at a single space" happens at the venue) ---
BROKER_PORT = 1883


def broker_host() -> str:
    return os.environ.get("NEURAROUTE_BROKER", "localhost")
