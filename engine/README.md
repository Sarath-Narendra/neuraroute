# engine/ — Decision Engine (owner: Sarath)

FastAPI + paho-mqtt + asyncio. The brain.

- Heartbeat ingest → in-memory **Resource Graph**; tiers go stale on a 3 s timeout.
- **Scheduler = the connectivity ladder:** pick the first tier that is alive and advertises
  `triage`, in fixed order `cloud-01 → pc-01 → phone-01 → arduino-01`. No cost function.
- **Planner:** one `triage` task per reading (no DAG). The orchestrator dispatches it, and on
  a stale/error/timeout re-routes one rung down the ladder — "internet down" surfaces as the
  cloud tier erroring, which is just another rung.
- Fans every raw reading out on `neuraroute/reading` (the arduino watchdog's input) and
  forwards watchdog `sos` alerts to the phone app. Emits every decision + reason to
  `neuraroute/event`.

**HTTP:** `POST /request` (`{patient_id, vitals}`), `GET /patients`, `GET /devices`,
`GET /ws` (WebSocket event stream to the phone app).

Run the whole stack with `./scripts/dev_up.sh` (broker + mock LLM + engine + 4 tiers).
