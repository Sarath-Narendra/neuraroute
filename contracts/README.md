# contracts/ — FROZEN v1 (owner: Sarath)

The shared language of the whole system. **Frozen and owned by Sarath.** Any change needs
his sign-off + a version bump + a note in the group chat. No silent edits, ever.

Everyone builds against the fakes here so nobody blocks anybody.

## Contents (to land Day 1)

- `heartbeat.schema.json` — device telemetry (battery, load, accelerators, alive)
- `task.schema.json` — engine → device dispatch
- `result.schema.json` — device → engine result
- `event.schema.json` — engine → dashboard decisions/reasons/failover/metrics
- `samples/*.json` — one valid sample payload per schema
- `fake_device.py` — N simulated devices: heartbeats with drifting battery/load, executes any task after a fake delay
- `fake_engine.py` — replays a canned decision-event stream for the dashboard
