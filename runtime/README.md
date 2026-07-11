# runtime/ — Device Agent (owner: Gowtham)

The universal Python agent that runs on every tier (Surface, OnePlus/Termux, Arduino UNO Q, cloud).

- `agent.py` reads `configs/<tier>.yaml` (`device_id`, `supported_ops`, `privacy_ok`).
- Publishes liveness heartbeats to `neuraroute/heartbeat`; subscribes to its task topic;
  runs `triage` via `models.run_model()`; publishes results.
- The **arduino** agent additionally runs the always-on **watchdog** (`watchdog: true`): it
  analyzes every reading on `neuraroute/reading` (tripwire + SLM), raises `sos` alerts, and
  writes verdicts to the STM32 serial bridge.

**Ports:** OnePlus 15 via Termux; Arduino UNO Q via its Debian side (see `docs/` runbooks).

`configs/` holds one YAML per tier. To run a tier against the mock LLM with no hardware,
use `scripts/dev_up.sh` (or point `NEURAROUTE_LOCAL_BASE_URL` at a real LM Studio server).
