# NeuraRoute — Resilient Edge AI for a Night Ward

**A single night-shift nurse, ten patients, and an AI brain that refuses to go dark.**
NeuraRoute forwards each patient's vitals to whichever AI backend is strongest and reachable
*at that moment* — GPT in the cloud when there's internet, the laptop or phone over the local
hotspot once that's gone, and a tiny model on an Arduino UNO Q as the final fallback — and it
**degrades gracefully** as each tier drops away. An always-on watchdog on the Arduino scans
every vital sign in parallel and pushes a **real notification straight to the doctor's phone**
the moment it detects a life-threatening emergency — even if the internet, the laptop, the
phone, and the server have all gone down.

Built for the **Snapdragon Multiverse Hackathon** (Bengaluru, Jul 11–12, 2026). The whole
system runs on a single laptop with **no cloud account and no AI hardware** — the models are
stubbed by a local mock server for development.

---

## The idea

Imagine a rural health center where a single nurse is monitoring ten patients through the
night. Every ~20 seconds, each patient's vitals (heart rate, SpO₂, temperature, respiration)
are captured and sent off for triage. NeuraRoute determines where that triage should run, and
ensures the nurse is alerted to anything critical no matter which pieces of infrastructure
have failed.

**The connectivity ladder** — the engine picks the first tier that is alive, in this order:

| Tier | Brain | When it runs |
|---|---|---|
| `cloud-01` | **GPT** (has full patient history) | internet is up |
| `pc-01` | Laptop local LLM | no internet, laptop on the hotspot |
| `phone-01` | Phone local LLM | laptop is down too |
| `arduino-01` | **UNO Q SLM** (records on-chip) | everything else is gone |

Each tier cross-references the reading against the patient's record and returns
`{severity: normal | mild | emergency, transcript}`. Pull the network (or `kill` a tier) and
the next reading slides down the ladder — live.

**The failsafe** — the UNO Q runs an *always-on watchdog* on **every** reading, independent of
the ladder, the internet, and even the engine: a hard numeric tripwire (`HR>135`, `SpO₂<85`, …)
**or** the local SLM flags an extreme emergency → the doctor's phone gets a real OS notification,
and the verdict prints to the Arduino IDE serial monitor while the on-board LED blinks.

---

## Architecture

```
  vitals reading (phone app / curl)
        │  POST /request
        ▼
   ┌──────────┐   neuraroute/task/<tier>    ┌─────────────────────────────┐
   │  ENGINE  │ ───────────────────────────▶│ tier agents (runtime/agent) │
   │ (ladder) │◀─────────────────────────── │ cloud · pc · phone · arduino │
   └────┬─────┘   neuraroute/result/<id>    └──────────────┬──────────────┘
        │  neuraroute/event (/ws)                          │ models.run_model("triage")
        │  neuraroute/reading ─────────────▶ arduino WATCHDOG (tripwire + SLM)
        ▼                                                   │ neuraroute/sos
   Doctor's PHONE APP (Expo)  ◀───────────────────────────┘
   patient board · tier status · 🚨 local notification
```

Everything talks over **MQTT** with **frozen JSON contracts** (`contracts/`). The engine
serves an HTTP + WebSocket API; the phone app connects to `/ws` over the local hotspot.
Broker address is one env var: **`NEURAROUTE_BROKER`**.

**MQTT topics (v2):**

| Topic | Direction | Purpose |
|---|---|---|
| `neuraroute/heartbeat` | tier → engine | liveness ping (~1.5 s) |
| `neuraroute/task/<device_id>` | engine → tier | triage dispatch |
| `neuraroute/result/<task_id>` | tier → engine | triage verdict |
| `neuraroute/reading` | engine → all | raw reading fan-out (watchdog input) |
| `neuraroute/sos` | watchdog → engine | extreme-emergency alert |
| `neuraroute/event` | engine → phone app | placements, failover, verdicts, sos |

---

## Repo layout

```
neuraroute/
  contracts/   # FROZEN schemas + samples + fakes (topics.py is the source of truth)
  engine/      # FastAPI + paho-mqtt + asyncio: the ladder scheduler + orchestrator
  models/      # run_model("triage", …) → {severity, transcript}; registry, LLM + GPT adapters, tripwire
  servers/     # the inference module: per-device POST /infer servers (laptop · cloud · phone)
  prompts/     # healthcare_system_prompt.txt — the shared triage system prompt
  runtime/     # agent.py (a tier) + configs/<tier>.yaml; the arduino agent runs the watchdog
  mobile/      # the doctor's phone app (Expo / React Native) — the UI
  arduino/     # UNO Q STM32 sketch: serial-monitor display + severity LED
  tools/       # mock_llm.py + mock_infer.py — OpenAI-compatible / /infer stubs (no model downloads)
  scripts/     # dev_up.sh (stack), infer_up.sh (/infer servers), kill_device.sh (failover trigger)
  data/        # patients.json — the 10-patient ward roster
  docs/        # hardware bring-up runbooks (UNO Q, phone/Termux)
```

---

## Prerequisites

- **Python 3.11+**
- **Mosquitto** — `brew install mosquitto` (macOS) / `apt install mosquitto` (Linux) / installer (Windows)
- **Node 20+** and the **Expo Go** app on your phone (for the mobile UI)

## Setup from scratch

```bash
git clone git@github.com:Sarath-Narendra/neuraroute.git
cd neuraroute

python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd mobile && npm install && cd ..    # phone app deps
```

## Run — the whole system on one laptop, no AI hardware

```bash
./scripts/dev_up.sh
```

This starts the broker, a **mock LLM** (so no model downloads or GPU are needed), the engine,
and all four tier agents. Then submit a reading and watch it triage:

```bash
# a critical reading -> emergency verdict + watchdog SOS  (engine is on :8080)
curl -XPOST localhost:8080/request -H 'Content-Type: application/json' \
     -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'

# drive the failover on stage: kill the top tier, submit again -> it routes one tier down
./scripts/kill_device.sh cloud-01
```

**The phone app:** `cd mobile && npx expo start`, then open it in **Expo Go** on a phone joined
to the laptop's network/hotspot. It auto-detects the engine at the laptop's IP (override in-app
if needed), shows the 10-patient board and tier status live, and raises a real OS notification on
every emergency.

## Use the real models (the inference module)

The engine is the **Router**; the real per-device model servers are a separate module (`servers/`)
that each expose `POST /infer` (laptop → GenieX/Qwen on `:8000`, cloud → Groq/Llama-70B on `:8001`,
phone → llama.cpp SLM on `:8002`). Start all three at once:

```bash
cp .env.example .env      # then set GROQ_API_KEY for the cloud tier
./scripts/infer_up.sh     # laptop :8000 · cloud :8001 · phone :8002
```

Then point the ladder at them with **venue mode** — the tier agents call `/infer` over HTTP and map
the reply into the phone app's schema:

```bash
export NEURAROUTE_REGISTRY=venue
export NEURAROUTE_INFER_LAPTOP_URL=http://<laptop-ip>:8000/infer   # default localhost:8000
export NEURAROUTE_INFER_CLOUD_URL=http://<cloud-host>:8001/infer   # default localhost:8001
export NEURAROUTE_INFER_PHONE_URL=http://<phone-ip>:8002/infer     # default localhost:8002
./scripts/dev_up.sh        # engine on :8080, agents bridge to the /infer servers
```

The engine, phone app, failover, and watchdog are unchanged — only where each tier runs inference
differs. Each `/infer` server still **boots** if its backend is missing (no `geniex`, no
`GROQ_API_KEY`, no on-device model) and returns a clean error, so a dead tier **fails over down the
ladder** instead of hanging — that's the demo. `arduino` stays on the local path
(`NEURAROUTE_LOCAL_BASE_URL`, e.g. llama.cpp) until its SLM `/infer` server lands. No contract
changes are needed to swap dev ↔ venue; flip `NEURAROUTE_REGISTRY` and restart.

To verify the bridge with no real models, run the mock `/infer` servers on the three ports — they
speak the exact `/infer` schema:

```bash
python tools/mock_infer.py 8000 laptop GenieX     Qwen3.5-2B
python tools/mock_infer.py 8001 cloud  Groq       llama-3.3-70b-versatile
python tools/mock_infer.py 8002 phone  llama.cpp  Qwen3-1.7B
```

---

## License

[MIT](LICENSE) — all dependencies are open-source (Mosquitto EPL, FastAPI/paho MIT,
React Native / Expo MIT, llama.cpp MIT, open-weights models with permissive licenses).
