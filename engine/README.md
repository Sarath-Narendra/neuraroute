# engine/ — Decision Engine (owner: Sarath)

FastAPI + paho-mqtt + asyncio. The brain.

- Heartbeat ingest → in-memory **Resource Graph**; devices go stale on a 3 s timeout.
- **Scheduler:** feasibility filter (alive, RAM, accelerator, privacy hard-constraint) →
  cost function `wL·L̂ + wE·Ê + wC·Ĉ − wP·P` → argmin. Weights in `policy.yaml`, hot-reloadable.
- **Hardcoded planner** for the health-report DAG (do NOT build a general planner):
  `t1 extract_text → (t2 summarize ∥ t3 flag_risk) → t4 patient_explainer`; `t3 → t5 population_stats`.
- **Failover:** missed heartbeat (>3 s) or task timeout → quarantine device → reschedule via the same scoring path. Emit every decision + human-readable reason to `neuraroute/event`.

**HTTP:** `POST /request` (PDF upload), `GET /ws` (WebSocket event stream to dashboard).

Test against `contracts/fake_device.py`.
