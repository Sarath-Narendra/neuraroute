# contracts/ — FROZEN v2 (owner: Sarath)

The shared language of the whole system. **Frozen and owned by Sarath.** Any change needs
his sign-off + a version bump (`CONTRACTS_VERSION` in `topics.py`) + a note in the group
chat. No silent edits, ever.

`topics.py` is the single source of truth for topic strings, op names, severity levels, and
the connectivity ladder — import from it, never hardcode.

## Contents

- `topics.py` — topics, `OP_TRIAGE`, severities, `PRIORITY_LADDER`, timing constants
- `heartbeat.schema.json` — tier → engine liveness ping (v2: liveness only, no telemetry)
- `task.schema.json` — engine → tier dispatch: `{patient_id, vitals, profile}`
- `result.schema.json` — tier → engine: `{patient_id, severity, transcript}`
- `event.schema.json` — engine → phone app: placements, failover, verdicts, sos
- `samples/*.json` — one valid sample payload per schema (+ `reading.json`)

To run the whole system with no models or hardware, use `tools/mock_llm.py` (an
OpenAI-compatible triage stub) — started automatically by `scripts/dev_up.sh`.
