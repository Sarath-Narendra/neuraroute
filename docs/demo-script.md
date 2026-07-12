# NeuraRoute — Presentation Demo Script

**The story:** a 10-patient night ward. Every vitals reading is triaged by AI, routed down a
**resilience ladder** (`Cloud → PC → Phone → Arduino`). As each layer dies, triage keeps running
on the next — live, no config changes. And an **always-on Arduino watchdog** raises an SOS to the
doctor's phone on any life-threatening reading, independent of the ladder, the internet, and even
the engine.

---

## 0. Before you present — the setup (have this running)

You need **3 terminals on the Surface** + the phone app.

| Terminal | Command | Leave it | Purpose |
|---|---|---|---|
| **A** | `./scripts/infer_up.sh` | running | the real model servers (cloud/PC/phone brains) |
| **B** | `export PATH="$PATH:/c/Program Files/mosquitto"` then `./scripts/dev_up.sh` | running | broker + engine + the 4 tiers (must show `registry=venue`) |
| **C** | *(free — you type kill commands here)* | — | drive the demo |

**Phone:** `cd mobile && npx expo start` (a 4th window) → Expo Go on the OnePlus → app shows **LIVE**.

**Preflight check (Terminal C) — do this 2 min before going on:**
```bash
curl -s localhost:8080/health
```
✅ All four must read `"alive":true`: `cloud-01, pc-01, phone-01, arduino-01`.
On the phone, the **tier strip** should show all four dots **green**.

> If a tier is missing/red: in Terminal B press Ctrl-C and re-run `dev_up.sh`; re-check health.

---

## 1. THE WARD  *(show the phone)*
**Say:** "One doctor, ten patients, night shift. Every reading is triaged by AI and routed down a
resilience ladder — cloud first, then the laptop, the phone, and finally a tiny Arduino."
**Show:** the ward list + the green tier strip (`Cloud › PC › Phone › Uno Q`), **LIVE** badge.

## 2. NORMAL READING → CLOUD answers (real AI)
**Do (on the phone):** tap a patient → tap **Normal** → **SEND READING**.
**Audience sees:** verdict comes back tagged **"GPT (cloud)"** in ~4 s.
**Say:** "Internet's up, so the smartest model — cloud — handles it. Real inference, not a script."

## 3. THE FAILOVER — kill the cloud *(the star of the show)*
**Do (Terminal C):**
```bash
./scripts/kill_device.sh cloud-01
```
**Audience sees:** the **Cloud dot goes dark** in the tier strip within ~3 s.
**Say:** "Now the internet drops." → **Do (phone):** tap a patient → **Critical** → **SEND**.
**Audience sees:** it routes to **"PC (local LLM)"** — your **Surface NPU** — and still answers.
(Give it ~15–25 s; on-device is slower than cloud — that's the point, it needs no internet.)
**Say:** "The ward never stopped. Triage moved on-device, to the Surface's NPU."

## 4. LOSE THE LAPTOP TOO → phone
**Do (Terminal C):**
```bash
./scripts/kill_device.sh pc-01
```
**Do (phone):** tap a patient → **Critical** → **SEND**.
**Audience sees:** the reading now lands on **"Phone (local LLM)"**.
**Say:** "Laptop's gone too — and it's still triaging, now on the phone itself."

## 5. THE WATCHDOG SOS — the safety net *(signature moment)*
**Say:** "Even if everything smart is down, one thing never sleeps — the Arduino watchdog. It checks
every reading against hard medical limits, no AI needed."
**Do (phone):** send another **Critical** reading (HR 176 / SpO₂ 79).
**Audience sees:** a red **🚨 EMERGENCY banner** slams onto the doctor's phone — raised by the
watchdog, not the ladder.
**Say:** "That alert fired independent of the cloud, the laptop, the phone model — even the engine.
That's the guarantee: a critical patient is never missed."

## 6. RECOVERY  *(optional, strong close)*
**Do (Terminal B):** press **Ctrl-C**, then re-run:
```bash
export PATH="$PATH:/c/Program Files/mosquitto"
./scripts/dev_up.sh
```
**Audience sees:** the tier strip lights back up green, top-down. Send a Normal reading → it's back on **Cloud**.
**Say:** "Connectivity returns, and readings climb right back up the ladder. Self-healing."

---

## Backup: drive it from the terminal (if the phone app hiccups)
Fire a reading without the app (Terminal C):
```bash
# Normal
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-01","vitals":{"hr":78,"spo2":97,"temp_c":36.8,"resp_rate":16}}'
# Critical
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-07","vitals":{"hr":182,"spo2":76,"temp_c":38.1,"resp_rate":34}}'
```
See which tier answered:
```bash
grep -a -E "dispatch|via|FAILOVER|SOS RAISED|done" run/logs/engine.log | tail -8
```

## Reset between rehearsals
Bring every killed tier back to green: **Ctrl-C Terminal B → re-run `dev_up.sh`** (Step 6).
That's a full clean reset of the ladder.

---

## The three commands you actually type on stage
```bash
./scripts/kill_device.sh cloud-01     # step 3
./scripts/kill_device.sh pc-01        # step 4
# step 6 (recover): Ctrl-C in Terminal B, then re-run dev_up.sh
```
Everything else is taps on the phone. **Rehearse it twice** before you present.
