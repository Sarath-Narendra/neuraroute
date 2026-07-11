# Runbook — OnePlus 15 phone bring-up (`phone-01`)

**Goal:** a live **`phone-01`** tier — the phone runs `agent.py` and serves `triage` as the
third rung of the connectivity ladder (used when cloud + PC are down).
**Owner:** Gowtham. **Rehearse Friday on your OWN Android phone** so Saturday is a repeat, not a first attempt.
**Budget:** 20–40 min.

> **Escalation ladder:** this runbook → 30 min stuck → mentor → pair with Abhiram (web/network) → **plan B (§ bottom).**
> **Why the phone tier matters:** it keeps triage running on the local hotspot after both the
> cloud and the laptop are gone — the second-to-last line of defense before the UNO Q.

---

## 0. Broker IP
Same as the Arduino runbook step 0 — get **`BROKER_IP`** from the broker PC and keep the phone on the **same hotspot**.

## 1. Install Termux + Termux:API (from F-Droid, NOT the Play Store)
The Play Store builds are outdated and broken. Install **both**:
- **Termux** app — https://f-droid.org/packages/com.termux/
- **Termux:API** app — https://f-droid.org/packages/com.termux.api/  (this is the companion APK, separate from the `termux-api` package)

**Expected:** Termux opens to a shell prompt.

## 2. Packages
```bash
pkg update && pkg upgrade -y
pkg install -y python git
pip install paho-mqtt pyyaml requests
```
**Expected:** `python --version` ≥ 3.11, `paho-mqtt` installs.
- **`pkg` fails to fetch** → phone has no internet; join the hotspot / check data.

## 3. The local SLM (the phone tier's brain)
The phone tier serves `triage` via an OpenAI-compatible endpoint. Simplest is llama.cpp's
server with a small Q4 model (e.g. Qwen2.5-1.5B) in Termux, then point the agent at it:
```bash
export NEURAROUTE_LOCAL_BASE_URL=http://localhost:1234/v1
```
- **No model ready yet?** Point `NEURAROUTE_LOCAL_BASE_URL` at the laptop's mock LLM
  (`tools/mock_llm.py`) so the tier still answers while you sort the on-device model.

## 4. Broker connectivity BEFORE the agent
```bash
python -c "import paho.mqtt.client as m; c=m.Client(m.CallbackAPIVersion.VERSION2); c.connect('BROKER_IP',1883); print('CONNECTED')"
```
**Expected:** `CONNECTED`.
- **refused/timeout** → same hotspot? broker PC firewall open on 1883? (see Arduino runbook step 5).

## 5. Deploy the agent + config
```bash
git clone https://github.com/Sarath-Narendra/neuraroute.git
cd neuraroute
```
`runtime/configs/phone.yaml`:
```yaml
device_id: phone-01
device_type: phone
supported_ops: [echo, triage]
privacy_ok: true
```

## 6. Run the agent → live tier
```bash
NEURAROUTE_BROKER=BROKER_IP NEURAROUTE_LOCAL_BASE_URL=http://localhost:1234/v1 \
  python runtime/agent.py runtime/configs/phone.yaml
```
**Expected, within ~2 s:**
- **phone app shows `phone-01` alive** in the tier strip
- engine log: `device phone-01 ALIVE`

Independent check:
```bash
mosquitto_sub -h BROKER_IP -t neuraroute/heartbeat -v      # phone-01 liveness every ~1.5 s
```

## 7. Prove it triages, and prove the failover
- With cloud + PC killed, submit a reading → it routes to `phone-01`; the phone app shows the
  verdict tagged "Phone (local LLM)".
- **On-stage kill:** `./scripts/kill_device.sh phone-01` (or Ctrl-C the agent) → within 3 s the
  tier goes stale and the next reading slides down to the UNO Q — live, on screen.

---

## Done when
- [ ] `phone-01` alive in the phone app's tier strip
- [ ] A reading routes to it (verdict tagged "Phone"); killing it fails the next reading over to `arduino-01`

## Plan B (§8) — if the loaner OnePlus blocks Termux / sideloading
The phone still runs the **doctor's app** (Expo Go), and a **laptop hosts the `phone-01`
tier** instead — just run the real agent for that config on any laptop on the hotspot:
```bash
python runtime/agent.py runtime/configs/phone.yaml   # phone-01 tier, hosted on a laptop
```
The ladder can't tell the difference — `phone-01` is a live tier either way, and killing it
(`./scripts/kill_device.sh phone-01`) drives the failover identically.

| Plan A | Plan B | Plan C |
|---|---|---|
| Termux agent on the real phone | Laptop hosts the `phone-01` tier (real agent) | Skip the phone tier; ladder routes cloud→pc→arduino |
