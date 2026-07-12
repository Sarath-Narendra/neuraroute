# NeuraRoute — Simple Demo Steps

Run every command in **Terminal C** on the Surface.
Each step: **cut a tier → fire a reading → see where it lands.**
Fire from the phone (tap patient → **Critical** → **SEND**) *or* use the curl in the block.
The `grep` shows which tier answered.

Decision tree:
```
reading ─▶ cloud-01 ─(kill)─▶ pc-01 ─(kill)─▶ phone-01 ─(kill)─▶ arduino-01
                                                                     │
            watchdog (tripwire) ───────────────────────────────▶ 🚨 SOS to phone
```

---

## PREFLIGHT — everything alive
```bash
curl -s localhost:8080/health
```
✅ all four read `alive:true`.

## STEP 0 — all up → CLOUD
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'; sleep 6; grep -a -E "dispatch|via" run/logs/engine.log | tail -2
```
Expect: `dispatch -> cloud-01` … `via GPT (cloud)`

## STEP 1 — cut CLOUD → PC (Surface NPU)
```bash
./scripts/kill_device.sh cloud-01
```
```bash
sleep 4; curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'; sleep 25; grep -a -E "FAILOVER|via" run/logs/engine.log | tail -3
```
Expect: `FAILOVER off cloud-01` … `-> pc-01` … `via PC (local LLM)`

## STEP 2 — cut PC → PHONE
```bash
./scripts/kill_device.sh pc-01
```
```bash
sleep 4; curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'; sleep 15; grep -a -E "FAILOVER|via" run/logs/engine.log | tail -3
```
Expect: `-> phone-01` … `via Phone (local LLM)`

## STEP 3 — cut PHONE → ARDUINO
```bash
./scripts/kill_device.sh phone-01
```
```bash
sleep 4; curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'; sleep 8; grep -a -E "FAILOVER|via" run/logs/engine.log | tail -3
```
Expect: `-> arduino-01` … `via Arduino (SLM)` — fully offline, last rung.

## STEP 4 — WATCHDOG SOS (independent of the ladder)
Cloud/PC/phone dead, fire a critical reading for a fresh patient:
```bash
curl -s -XPOST localhost:8080/request -H 'Content-Type: application/json' -d '{"patient_id":"P-07","vitals":{"hr":182,"spo2":76,"temp_c":38.1,"resp_rate":34}}'; sleep 3; grep -a "SOS RAISED" run/logs/arduino-01.log | tail -2
```
Expect: `SOS RAISED for P-07: tripwire: hr 182 > 135 bpm; spo2 76 < 85 %` → phone shows the 🚨 EMERGENCY banner.

## RESET — bring every tier back to green
In **Terminal B**: press **Ctrl-C**, then:
```bash
export PATH="$PATH:/c/Program Files/mosquitto"; ./scripts/dev_up.sh
```

---

**The 3 commands you actually type on stage:**
```bash
./scripts/kill_device.sh cloud-01
./scripts/kill_device.sh pc-01
./scripts/kill_device.sh phone-01
```
Everything else is taps on the phone.
