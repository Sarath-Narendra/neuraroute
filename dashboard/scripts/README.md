# scripts/ — Orchestration scripts (owner: Gowtham)

One-command lifecycle for the whole system. `main` must always run `dev_up.sh` cleanly.

- `dev_up.sh` — start broker + engine + N fake devices (the full system in simulated mode)
- `demo_reset.sh` — reset to demo-start state in <60 s
- `kill_device.sh` — kill a device node on cue (drives the on-stage failover)
