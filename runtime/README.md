# runtime/ — Device Agent (owner: Gowtham)

The universal Python agent that runs on every node (Surface, OnePlus/Termux, Arduino Uno Q).

- `agent.py` reads `configs/<device>.yaml` (device_id, accelerators, models, telemetry mode: `real|simulated`).
- Publishes heartbeats to `neuraroute/heartbeat`; subscribes to its task topic; executes ops via Eswar's `run_model()`; publishes results.
- Simulated telemetry mode (scripted battery drain for the safe on-stage failover) + `simulate_battery_critical` admin handler.

**Ports:** OnePlus 15 via Termux; Arduino Uno Q via its Debian side (agent deployed after Sarath's bring-up).

`configs/` holds one YAML per device. Test against `contracts/fake_engine.py`.
