# Test the REAL ladder on the Surface — baby steps

Goal: prove **internet ON → cloud**, **internet OFF → Surface**, **kill PC tier → phone**.
Do these in order. Each step has a **See:** line — if you see it, go on.

> **On the Surface use Git Bash** (not PowerShell) for all commands below.
> Each Git Bash window is a fresh shell — that's why some commands re-set `PATH`.

---

## STEP 0 — Push from your Mac (do this once, on the Mac)
```bash
git add -A && git commit -m "real-mode test" && git push origin main
```
**See:** push succeeds. (Your `.env` with the key does NOT upload — it's gitignored. Good.)

---

## STEP 1 — Get the code on the Surface
Open **Git Bash**, then:
```bash
cd ~/neuraroute            # or wherever you cloned it; first time: git clone <repo-url> && cd neuraroute
git pull origin main
pwd && ls scripts/dev_up.sh
```
**See:** it prints the path and `scripts/dev_up.sh` exists.

---

## STEP 2 — One-time checks (skip if already done before)

**2a. Broker installed?**
```bash
ls "/c/Program Files/mosquitto/mosquitto.exe"
```
**See:** the file path prints. If "No such file" → install Mosquitto (Windows x64 installer from https://mosquitto.org/download/), then retry.

**2b. Python deps present?**
```bash
.venv/Scripts/python.exe -c "import paho.mqtt.client, fastapi, uvicorn, yaml, requests; print('deps OK')"
```
**See:** `deps OK`. If it errors → `.venv/Scripts/python.exe -m pip install -r requirements.txt` then retry.

---

## STEP 3 — Turn on REAL mode in `.env`
Open `.env` in the repo and make sure it has these lines (add the key, keep the rest):
```
NEURAROUTE_REGISTRY=venue
GROQ_API_KEY=gsk_your_real_key_here
NEURAROUTE_BROKER=localhost
```
**See:** the file saved with your real `gsk_...` key.

---

## STEP 4 — Start the model servers (Terminal A)
Open a **first** Git Bash window:
```bash
cd ~/neuraroute
./scripts/infer_up.sh
```
**See:** three lines — `infer_laptop :8000`, `infer_cloud :8001`, `infer_phone :8002`. **Leave this window open.**

---

## STEP 5 — Start the broker + engine + tiers (Terminal B)
Open a **second** Git Bash window:
```bash
cd ~/neuraroute
export PATH="$PATH:/c/Program Files/mosquitto"
./scripts/dev_up.sh
```
**See:** a banner ending with `NeuraRoute up (registry=venue). Engine: http://<IP>:8080`.
**Write down that `<IP>`** (the phone will use it). **Leave this window open.**

---

## STEP 6 — Confirm all tiers are alive (Terminal C)
Open a **third** Git Bash window:
```bash
cd ~/neuraroute
curl -s localhost:8080/health | .venv/Scripts/python.exe -c "import sys,json; d=json.load(sys.stdin)['devices']; print({k:v['alive'] for k,v in d.items()})"
```
**See:** `{'cloud-01': True, 'pc-01': True, 'phone-01': True, 'arduino-01': True}`.

---

## STEP 7 — Fire a reading and see WHICH tier answered
In Terminal C:
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' \
  -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'
echo; sleep 3
grep -E "DONE|via|FAILOVER" run/logs/engine.log | tail -5
```
**See (internet ON):** a line with **`via GPT (cloud)`** → cloud answered. ✅ **Ladder step 1 works.**

---

## STEP 8 — Test failover #1: internet OFF → Surface
1. **Turn off the internet** (on Phone A: turn off mobile data, but **keep the hotspot ON**).
2. In Terminal C, fire again + read the log:
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' \
  -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'
echo; sleep 4
grep -E "FAILOVER|via" run/logs/engine.log | tail -5
```
**See:** `FAILOVER ... -> pc-01` then `via PC (local LLM)`. ✅ **Ladder step 2 works** (runs on the Surface).

---

## STEP 9 — Test failover #2: kill PC tier → phone
> ⚠️ Do NOT close the Surface — it's the hub. Just stop the PC tier.
```bash
./scripts/kill_device.sh pc-01
sleep 4
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' \
  -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'
echo; sleep 4
grep -E "FAILOVER|via" run/logs/engine.log | tail -5
```
**See:** `-> phone-01` then `via Phone (local LLM)`. ✅ **Ladder step 3** — *only if the phone is running its own model + agent.* If instead you see it skip to `arduino-01`, the phone tier isn't serving a model yet.

---

## STEP 10 — Add the phone app (optional, for the visual)
```bash
cd mobile && npx expo start
```
Open in **Expo Go** on the OnePlus (same hotspot). It auto-finds the Surface `<IP>`.
Fire readings from the app's patient cards and watch the tier light up.

---

## If something's red — quick fixes
| Problem | Fix |
|---|---|
| `dev_up: mosquitto not found` | You forgot `export PATH="$PATH:/c/Program Files/mosquitto"` in THAT window (Step 5). |
| a tier is `False` in Step 6 | Read its log: `run/logs/<device>.log` (e.g. `run/logs/pc-01.log`). |
| cloud never answers even with internet | `GROQ_API_KEY` missing/typo in `.env`, or `infer_up.sh` (Terminal A) not running. |
| phone never catches the handoff (Step 9) | The phone isn't running a model + `phone-01` agent — expected if you haven't set that up yet. |

## To stop everything
Press **Ctrl-C** in Terminal A and Terminal B.
