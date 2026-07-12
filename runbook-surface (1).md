Runbook — Venue bring-up from the Surface (execute this, Claude)

> **You are Claude Code running on the Surface laptop (the hub).** This runbook is yours to
> execute, top to bottom, one phase at a time. After each phase: report a **one-line status**
> to the human, and **wait** whenever a step is marked 🙋 (needs the human or the UNO Q board).
> Never skip the **VERIFY** step. If a phase overruns its budget, fall back (see bottom) and move on.

---

## Context — read once
- **Project:** NeuraRoute — vitals triage routed down a connectivity ladder
  (`cloud-01 → pc-01 → phone-01 → arduino-01`), failing over live as tiers die, plus an
  **always-on Arduino watchdog** that raises an SOS to the doctor's phone on any life-threatening
  reading — independent of the ladder, the internet, and even the engine. Full detail in `README.md`.
- **The Surface is the HUB.** In **dev mode** (the default) it runs *everything* on one machine with
  mocks: the MQTT broker + the engine + a mock LLM + all four tier agents. **No real models, no cloud
  account, no GPU needed.** That is the demo's safety net — get it green first (Phase 0).
- **The SLM is NOT built yet** (`models/arduino.py` is a marked stub). **This does not matter today:**
  the watchdog SOS fires from a hard numeric **tripwire** (HR/SpO₂/temp/resp bounds), not from a model,
  and the ladder failover is 100% real. Only the *wording* of each verdict is canned in dev mode. Judges
  see real orchestration. Do **not** try to build the SLM here.
- **Stay in dev mode.** Do **NOT** set `NEURAROUTE_REGISTRY=venue` — that points tiers at real
  GenieX/Groq `/infer` servers which are not set up. Default (dev) is correct for the demo.

## What you can and cannot do
- ✅ **You do autonomously:** Phase 0 (bring up + verify the hub) and Phase 4 (drive the demo).
- 🙋 **You cannot:** flash the STM32 (Arduino IDE is a GUI — the human clicks *Upload*) or open a shell
  on the UNO Q's Linux side (a separate computer). For those, give the human **exact** instructions and
  **wait**; then **verify the result from the Surface** (heartbeats / logs / `/health`).

## Environment
- **OS:** Windows on ARM. **Shell:** Git Bash (your Bash tool).
- ⚠️ **Each of your Bash calls is a fresh shell — environment does NOT persist between calls.** When a
  command needs the `mosquitto` binary, set PATH **inline in that same call** (shown below). Don't rely
  on a previous `export`.
- **Repo:** your current working directory (confirm with `pwd`; it must contain `scripts/dev_up.sh`).
- **venv:** already present at `.venv/Scripts/python.exe`. dev_up.sh auto-detects it.
- **Mosquitto dir (once installed):** `/c/Program Files/mosquitto` — reused throughout as the PATH add.

## Time discipline
Target **Phases 0–4 in ≈2 h**, then **FREEZE**: the **7:00 AM–1:00 PM** window is *debug + rehearse only*,
submission at **1:00 PM**. Hard cutoffs + fallback ladder are at the bottom. When the clock says fall
back, fall back — the demo needs a live tier and a working SOS, not a heroic debugging story.

---

# Phase 0 — Surface hub in dev mode (you do this alone)

### 0.1 — Pull the latest code
```bash
pwd && ls scripts/dev_up.sh          # confirm you're in the repo root
git pull origin main
```
- **If pull is blocked by local changes to `.claude/settings.local.json`:**
  `git stash && git pull origin main && git stash pop`

### 0.2 — Make sure the broker (mosquitto) is installed
```bash
command -v mosquitto || ls "/c/Program Files/mosquitto/mosquitto.exe"
```
- **If found** → continue to 0.3.
- **If MISSING** → 🙋 ask the human to install it (needs admin). Give them, in order:
  1. `winget search mosquitto`  → then `winget install --id <ID from the Eclipse row>`
  2. **or** download the **Windows x64 installer** from https://mosquitto.org/download/ and run it
     (x64 runs fine under Windows-on-ARM emulation; it installs to `C:\Program Files\mosquitto\`).
  **Wait** for them to finish, then re-run the check above until it resolves.

### 0.3 — Verify Python deps
```bash
.venv/Scripts/python.exe -c "import paho.mqtt.client, fastapi, uvicorn, yaml, requests; print('deps OK')"
```
- **If it errors** → `.venv/Scripts/python.exe -m pip install -r requirements.txt` then re-check.

### 0.4 — Start the whole stack (run in the BACKGROUND, PATH set inline)
Run this as a **background** command (it runs until Ctrl-C):
```bash
export PATH="$PATH:/c/Program Files/mosquitto"; ./scripts/dev_up.sh
```
This starts, in order: **mosquitto** (via `scripts/mosquitto.conf` → binds `0.0.0.0:1883`, anonymous —
so the phone/UNO Q can connect), **mock_llm** (:1234), **engine** (:8080), and the **4 tier agents**.

### 0.5 — VERIFY the hub is healthy
```bash
# wait (bounded) for the engine, then check all four tiers are alive
for i in $(seq 1 25); do curl -sf localhost:8080/health >/dev/null 2>&1 && { echo "engine up (${i}s)"; break; }; sleep 1; done
curl -s localhost:8080/health | .venv/Scripts/python.exe -c "import sys,json; d=json.load(sys.stdin)['devices']; print({k:v['alive'] for k,v in d.items()})"
```
**Expect:** `{'cloud-01': True, 'pc-01': True, 'phone-01': True, 'arduino-01': True}`.
- **A tier missing / False** → read its log: `run/logs/<device>.log` (e.g. `run/logs/pc-01.log`) for a traceback.
- **`engine up` never prints** → read `run/logs/engine.log` and `run/logs/mosquitto.log`.

Also capture the **engine LAN IP** (the phone app will point here) — it's printed in the dev_up banner
as `Engine: http://<IP>:8080`. Report that IP to the human.

### 0.6 — VERIFY the watchdog fires (the money shot)
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' \
     -d '{"patient_id":"P-07","vitals":{"hr":182,"spo2":76,"temp_c":38.1,"resp_rate":34}}'
echo
sleep 3
grep -E "SOS RAISED|emergency" run/logs/arduino-01.log run/logs/engine.log | tail -5
```
**Expect:** `SOS RAISED for P-07: tripwire: hr 182 > 135 bpm; spo2 76 < 85 %` in `arduino-01.log`, and the
engine logging the run as `emergency`.

### ✅ Phase 0 DONE when
- dev_up banner shows **mosquitto + mock_llm + engine + 4 agents**
- `/health` shows **all 4 tiers alive**
- a critical reading yields **`SOS RAISED`** in `run/logs/arduino-01.log`

**Report to the human:** `Phase 0 PASS — hub live at http://<IP>:8080, all 4 tiers up, watchdog SOS confirmed.`
You now have a full, demoable system even if the physical Arduino never comes up. Everything below adds it.

---

# Phase 1 — Flash the STM32 🙋 (human clicks; you prep + wait)
The physical Arduino's display/LED is programmed via the **Arduino IDE GUI** — you can't drive it. Give the
human these exact steps and **wait** for confirmation:

> 1. Plug the UNO Q into the Surface with a **data** USB-C cable.
> 2. Arduino IDE → **Boards Manager** → search **"UNO Q"** → install the Arduino UNO Q board package.
> 3. **File → Open** → `arduino/neuraroute_monitor/neuraroute_monitor.ino`
> 4. **Tools → Board** = Arduino UNO Q · **Tools → Port** = the UNO Q port → click **Upload**.
> 5. **Tools → Serial Monitor** → set baud **115200**.
> **Expect on the monitor:** `== NeuraRoute UNO Q monitor ready ==`

- **No port shown** → different data USB-C cable / port. **Upload error** → wrong Board or Port selected.
- The LED won't react yet (it waits for verdicts from the Linux side — that's Phase 3). The banner is enough.

**Wait for the human to confirm the banner**, then continue.

---

# Phase 2 — UNO Q Linux agent → green `arduino-01` 🙋 (human on the board; you verify)

### 2.1 — On the Surface (you): free up the `arduino-01` slot
The hub is already running a stand-in `arduino-01`. Two agents with the same id fight over MQTT — kill the
stand-in first:
```bash
./scripts/kill_device.sh arduino-01
```

### 2.2 — 🙋 Ask the human to bring up the real tier on the UNO Q
Give them this (from `docs/runbook-arduino.md`). `SURFACE_IP` = the engine IP from Phase 0.5.
> On the UNO Q **Linux side** (Arduino App Lab → Linux terminal, or ssh), on the **same hotspot** as the Surface:
> ```bash
> ping -c 3 SURFACE_IP                                   # must reply
> pip3 install paho-mqtt pyyaml requests                 # add --break-system-packages if needed
> git clone https://github.com/Sarath-Narendra/neuraroute.git && cd neuraroute
> NEURAROUTE_BROKER=SURFACE_IP \
> NEURAROUTE_LOCAL_BASE_URL=http://SURFACE_IP:1234/v1 \
>   python3 runtime/agent.py runtime/configs/arduino.yaml
> ```

### 2.3 — VERIFY from the Surface (you)
```bash
sleep 3
grep "arduino-01 ALIVE" run/logs/engine.log | tail -1
curl -s localhost:8080/health | .venv/Scripts/python.exe -c "import sys,json; print('arduino-01 alive:', json.load(sys.stdin)['devices'].get('arduino-01',{}).get('alive'))"
```
**Expect:** `arduino-01 ALIVE` in the engine log and `arduino-01 alive: True`.
- **Never goes alive** → networking, not code. #1 cause: **Windows Defender blocking inbound TCP 1883**
  on the Surface — tell the human to open it. Also confirm both machines are on the same hotspot and the
  UNO Q used the correct `SURFACE_IP`.

**Report:** `Phase 2 PASS — arduino-01 now served by the real UNO Q.`

---

# Phase 3 — Serial bridge → LED + transcripts 🙋 (human on the board; you fire)

### 3.1 — 🙋 Ask the human (on the UNO Q)
> Find the Linux↔MCU bridge UART: `ls /dev/ttyAMA* /dev/ttyHS* 2>/dev/null` (usually `/dev/ttyAMA0`).
> Edit `runtime/configs/arduino.yaml`: set `serial_port: /dev/ttyAMA0` (was `null`). **Restart** the agent
> (re-run the 2.2 command).

### 3.2 — You fire a critical reading
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' \
     -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'
```
**Human confirms** on the Arduino IDE Serial Monitor: a line like `[P-03] EMERGENCY (watchdog): ...` and the
on-board **LED fast-blinks**. (Normal reading → LED off; mild → solid.)
- **Nothing on the monitor** → wrong `serial_port`, or baud ≠ 115200. If the agent log shows `[SERIAL] ...`
  but the monitor is blank, the bridge UART device is wrong.

---

# Phase 4 — Rehearse the demo (you drive, 2–3× each)
Subscribe to events **before** firing so you catch the instant ones (or just tail `run/logs/engine.log`).

**A. Failover down the ladder**
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-01","vitals":{"hr":88,"spo2":96,"temp_c":37,"resp_rate":16}}'
./scripts/kill_device.sh cloud-01     # next reading routes to pc-01
# fire again → then kill pc-01 → phone-01 → arduino-01, firing between each
grep -E "placement|FAILOVER|DONE" run/logs/engine.log | tail -12
```
Show the human the `placement ... -> <tier>` and `FAILOVER` lines walking down the ladder.

**B. Watchdog SOS with everything killed** (the signature moment)
```bash
./scripts/kill_device.sh cloud-01; ./scripts/kill_device.sh pc-01; ./scripts/kill_device.sh phone-01
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-07","vitals":{"hr":182,"spo2":76,"temp_c":38.1,"resp_rate":34}}'
sleep 2; grep "SOS RAISED" run/logs/arduino-01.log | tail -1
```
Even with cloud/pc/phone dead, the watchdog still raises the SOS (+ the LED panics if Phase 3 is done).

**C. Recovery** — restart the stack (or individual tiers) and show readings climbing back up the ladder.
To restart everything cleanly: stop the dev_up background process, then re-run 0.4.

---

# Troubleshooting (Windows-on-ARM)
| Symptom | Fix |
|---|---|
| dev_up: `mosquitto not found` | You didn't set PATH in that shell. Prepend `export PATH="$PATH:/c/Program Files/mosquitto";` (your Bash calls don't persist env). |
| devices can't connect / `connection refused` | Open **Windows Defender inbound TCP 1883** on the Surface. #1 venue blocker. |
| a tier tile is red after ~3 s | That agent crashed — read `run/logs/<device>.log` for the traceback. |
| `arduino-01` heartbeat flapping | Two `arduino-01`s (hub + UNO Q). Run `./scripts/kill_device.sh arduino-01` on the Surface. |
| `git pull` blocked | Local change to `.claude/settings.local.json` → `git stash && git pull origin main && git stash pop`. |
| kill_device says "PID file not found" | The stack isn't running, or dev_up didn't start that tier. Re-run 0.4. |

# Fallback ladder (protect the 6 h debug buffer)
| Plan A | Plan B | Plan C |
|---|---|---|
| UNO Q agent + serial LED (Phases 2–3) | UNO Q agent, `serial_port: null` — real tier + real SOS, no LED | **`arduino-01` hosted on the Surface** (Phase 0 already does this) — bulletproof, costs hardware points |

**Hard cutoff:** if Phase 2 (the UNO Q tier) isn't ALIVE within ~45 min of trying, fall to **Plan C** and
**stop building**. Phase 0 alone is a complete, winnable demo.

# How to report after each phase
`Phase N: PASS | BLOCKED — <one line>. Next: <the single command the human must run, or "you continue">.`
