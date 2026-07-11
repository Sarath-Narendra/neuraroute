# Runbook — OnePlus 15 phone bring-up (`phone-01`)

**Goal:** a green **`phone-01`** tile with **real battery telemetry** (the battery bar reflects the actual phone).
**Owner:** Gowtham. **Rehearse Friday on your OWN Android phone** so Saturday is a repeat, not a first attempt.
**Budget:** 20–40 min.

> **Escalation ladder:** this runbook → 30 min stuck → mentor → pair with Abhiram (web/network) → **plan B (§ bottom).**
> **Why real battery matters:** the battery bar draining live is what sells "battery-aware routing." If Termux is blocked, plan B keeps a real tile with simulated telemetry.

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
pkg install -y python termux-api git
pip install paho-mqtt pyyaml
```
**Expected:** `python --version` ≥ 3.11, `paho-mqtt` installs.
- **`pkg` fails to fetch** → phone has no internet; join the hotspot / check data.

## 3. Real battery telemetry works
```bash
termux-battery-status
```
**Expected:** JSON like `{"percentage": 78, "plugged": "UNPLUGGED", ...}` (a permission prompt may appear the first time — **Allow**).
- **`termux-battery-status: command not found` or hangs forever** → the **Termux:API app** (step 1) isn't installed or lacks permission. Install it from F-Droid and re-run. This is the #1 phone gotcha.

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
`runtime/configs/phone-01.yaml`:
```yaml
device_id: phone-01
accelerators: [cpu, npu]
models: [summarize, flag_risk, patient_explainer]
telemetry_mode: real          # battery via termux-battery-status
```

## 6. Run the agent → green tile with a live battery bar
```bash
NEURAROUTE_BROKER=BROKER_IP python runtime/agent.py runtime/configs/phone-01.yaml
```
**Expected, within ~2 s:**
- **dashboard shows a green `phone-01` tile** whose **battery bar matches the phone's real %**
- engine log: `device phone-01 ALIVE`

Independent check:
```bash
mosquitto_sub -h BROKER_IP -t neuraroute/heartbeat -v      # phone-01 heartbeats with real battery
```

## 7. Prove the telemetry is real (this is the on-stage failover fuel)
- **Unplug** the phone → over ~30 s the battery % on the tile ticks **down**.
- **Plug in** → the `charging` flag flips and the bar behavior changes.
- **Safe on-stage kill:** the agent honours `simulate_battery_critical` from `neuraroute/admin`, so the demo drops the tile without physically unplugging:
  ```bash
  mosquitto_pub -h BROKER_IP -t neuraroute/admin -m '{"cmd":"simulate_battery_critical","device_id":"phone-01"}'
  ```
  **Expected:** battery reads critical → engine re-routes any in-flight task off `phone-01` with a reason on screen.

---

## Done when
- [ ] Green `phone-01` tile with **real** battery telemetry, on the projector
- [ ] Battery % changes when you unplug/plug; `simulate_battery_critical` triggers a live re-route

## Plan B (§8) — if the loaner OnePlus blocks Termux / sideloading
The phone becomes the **browser dashboard UI node only** (open the dashboard in its Chrome), and a **laptop-hosted agent masquerades as `phone-01`** with simulated telemetry:
```bash
python -m contracts.fake_device phone-01          # on any laptop on the hotspot
```
Still a real, live tile on screen — the audience can't tell, and the battery-drain script (`simulate_battery_critical`) works identically.

| Plan A | Plan B | Plan C |
|---|---|---|
| Termux agent + real battery telemetry | Browser UI + masqueraded agent w/ simulated telemetry | Fake device labeled `phone-01` |
