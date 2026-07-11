# scripts/ — Orchestration scripts

One-command lifecycle for the whole system.

- `dev_up.sh` — start the full stack on one laptop: broker + mock LLM + engine + the 4 tier
  agents (cloud, pc, phone, arduino). No models or hardware needed.
- `demo_reset.sh` — kill the running stack, archive logs, and relaunch via `dev_up.sh`.
- `kill_device.sh <device_id>` — hard-kill a tier on cue (drives the on-stage failover),
  e.g. `./scripts/kill_device.sh cloud-01`.
