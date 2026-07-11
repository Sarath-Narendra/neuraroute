# NeuraRoute — Adaptive AI Inference Orchestrator

**The "Kubernetes of AI": a software orchestration layer that decides at runtime *which
device* runs each AI task — and re-routes live when conditions change.** Four Snapdragon
devices behave as one cooperative AI computer, with routing decisions made on-device based
on battery, latency, thermal, privacy, and cost signals — plus graceful degradation and
live failover.

Built for the **Snapdragon Multiverse Hackathon** (Bengaluru, Jul 11–12, 2026).

---

## Team

| Role | Name | Component | Owns folder |
|---|---|---|---|
| Lead / Engine / Integration / Presenter | **Sarath Narendra Kuppala** | Decision engine, contracts, Arduino Uno Q bring-up | `engine/`, `contracts/` |
| Dashboard | **Abhiram** | React dashboard, WebSocket client, CI, README acid test | `dashboard/` |
| Runtimes / Devices | **Gowtham** | Universal device agent, phone/Uno Q ports, broker, scripts | `runtime/`, `scripts/` |
| Models / Cloud / Metrics | **Eswar** | The 5 model ops, cloud adapter, benchmark, docs | `models/`, `metrics/`, `docs/` |

_Contact emails are listed in the submission form and will be added here before submission._

---

## How it works

Every component talks over **MQTT** with **frozen JSON contracts** (owned by the engine
lead — see `contracts/`). Each person builds against *fakes* of everyone else's component,
so nobody blocks anybody. Integration = pointing every process at the same broker.

**MQTT topics (v1):**

| Topic | Direction | Purpose |
|---|---|---|
| `neuraroute/heartbeat` | device → engine | telemetry every 1–2 s |
| `neuraroute/task/<device_id>` | engine → device | task dispatch |
| `neuraroute/result/<task_id>` | device → engine | task result |
| `neuraroute/event` | engine → dashboard | decisions, reasons, failover, metrics |
| `neuraroute/admin` | control | demo controls (`simulate_battery_critical`, `reset`) |

The broker address is read from a single env var: **`NEURAROUTE_BROKER`**.

---

## Repo layout

```
neuraroute/
  contracts/   # FROZEN schemas + sample payloads + fakes (owner: Sarath)
  engine/      # FastAPI + paho-mqtt + asyncio decision engine (Sarath)
  dashboard/   # Vite + React + Tailwind, WebSocket client (Abhiram)
  runtime/     # agent.py + configs/<device>.yaml (Gowtham)
  models/      # run_model(op, payload) + cloud_adapter.py (Eswar)
  metrics/     # run_bench.py -> metrics.json (Eswar)
  scripts/     # dev_up.sh, demo_reset.sh, kill_device.sh
  docs/        # pitch, runbooks
```

---

## Prerequisites

- **Python 3.11+**
- **Node 20+**
- **Mosquitto** MQTT broker — `brew install mosquitto` (macOS) / installer (Windows) / `apt install mosquitto` (Linux)
- **Git**

## Setup from scratch

```bash
git clone git@github.com:Sarath-Narendra/neuraroute.git
cd neuraroute

# Python side (engine, runtime, models, metrics)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # added as components land

# Dashboard
cd dashboard && npm install && cd ..

# Broker address (defaults to localhost)
export NEURAROUTE_BROKER=localhost  # Windows: set NEURAROUTE_BROKER=localhost
```

## Run (simulated-device mode — everything on one laptop)

```bash
./scripts/dev_up.sh     # starts broker + engine + fake devices
cd dashboard && npm run dev
```

A judge can run the **entire system on a single laptop** in simulated-device mode — no
physical Snapdragon hardware required.

---

## Contributing (team)

- **Commit only inside your own folder.** Folder-per-owner = zero merge conflicts by construction.
- `main` must always run `scripts/dev_up.sh` cleanly. If your push breaks it, fix it before anything else.
- **`contracts/` is frozen and owned by Sarath.** Any schema change needs sign-off + a version bump + a note in the group chat. No silent edits.
- Commit often (~every 30 min) with a clear message ("working X against fake Y").

## License

[MIT](LICENSE) — all dependencies are open-source (Mosquitto EPL, FastAPI/paho MIT,
React MIT, llama.cpp MIT, open-weights models with permissive licenses).
