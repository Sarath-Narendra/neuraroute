# Runbook — Arduino UNO Q bring-up (`arduino-01`)

**Goal:** a green **`arduino-01`** tile heartbeating on the dashboard, able to run one dispatched op.
**Owner of bring-up:** Sarath (embedded lane). **Executor if he's unavailable:** anyone — follow these steps literally.
**Window:** Saturday 9:00–11:00 AM (before the hack clock), Gowtham shadowing. Budget 30–60 min.
**Scope:** the Qualcomm (Dragonwing) **Debian Linux** side only. No firmware, no MCU code, no wiring — the STM32 half stays untouched.

> **Escalation ladder (never skip a rung):** this runbook → 30 min stuck → onsite mentor → pair with Sarath (max 45 min) → **fallback (§ bottom).**
> **Saturday timebox:** not heartbeating by **3:00 PM → switch to the plan-B op**; not live by **Checkpoint 1 (5:00 PM) → simulate `arduino-01` and never look back.**

---

## 0. Before you touch the board — get the broker IP

Every device points at one broker via `NEURAROUTE_BROKER`. On the **PC hosting the broker** (the Surface):

```powershell
ipconfig            # Windows: note the hotspot adapter's IPv4, e.g. 192.168.137.1
```
```bash
ipconfig getifaddr en0   # macOS
hostname -I              # Linux
```

Write it down as **`BROKER_IP`**. Confirm the broker is actually listening:
```bash
# on the broker PC
mosquitto_sub -h localhost -t 'neuraroute/#' -v      # should sit and wait (Ctrl-C to stop)
```
- **If `mosquitto_sub` errors "connection refused"** → the broker isn't running. Start it: `mosquitto -p 1883` (or `scripts/dev_up.sh`).

---

## 1. Power the board

USB-C → wait **60–90 s** for the Qualcomm side to boot Debian on its own.

**Expected:** power LED on; after ~90 s it behaves like a small Linux computer.
- **No LED / nothing after 2 min** → swap to a known **data-capable** USB-C cable and a different port; then a powered USB hub. Still dead → mentor.

## 2. Get a shell on the Linux side

**Option A — Arduino App Lab** (GUI): open App Lab → the board's Linux terminal.
**Option B — ssh** (after Wi-Fi, step 3): `ssh <user>@<board-ip>`.

**Expected:** a bash prompt. Verify it's the Linux side:
```bash
uname -a        # expect: Linux ... aarch64
```
- **Prompt but `uname` says something odd / no aarch64** → you may be on the wrong console; use App Lab's Linux terminal, not the MCU serial monitor.

## 3. Join the hotspot Wi-Fi

Via App Lab Wi-Fi settings, or on the shell:
```bash
nmcli dev wifi connect "<HOTSPOT_SSID>" password "<HOTSPOT_PASSWORD>"
nmcli -t -f active,ssid dev wifi        # expect: yes:<HOTSPOT_SSID>
ping -c 3 BROKER_IP                     # expect: 3 replies, no loss
```
**Expected:** ping to `BROKER_IP` succeeds.
- **`ping` fails / 100% loss** → (a) confirm the board and the broker PC are on the **same hotspot**; (b) turn OFF the broker PC's firewall for port 1883 (Windows Defender blocks inbound mosquitto by default); (c) re-run step 0's `mosquitto_sub` to confirm the broker is up. **This is a networking problem, not a code problem — do not touch the agent yet.**

## 4. Python + MQTT client

```bash
python3 --version                       # need >= 3.9; if missing:
sudo apt update && sudo apt install -y python3 python3-pip
pip3 install paho-mqtt pyyaml           # if "externally-managed-environment":
pip3 install --break-system-packages paho-mqtt pyyaml
```
**Expected:** `paho-mqtt` installs without error.

## 5. Prove broker connectivity BEFORE running the agent

This isolates networking from the agent code — always do it:
```bash
python3 -c "import paho.mqtt.client as m; c=m.Client(m.CallbackAPIVersion.VERSION2); c.connect('BROKER_IP',1883); print('CONNECTED')"
```
**Expected:** prints `CONNECTED`.
- **`ConnectionRefusedError` / timeout** → networking (go back to step 3). The broker PC firewall is the #1 culprit at venues.

## 6. Deploy the agent + its config

Get Gowtham's agent onto the board (either clone the repo or scp two files):
```bash
git clone https://github.com/Sarath-Narendra/neuraroute.git
cd neuraroute
```
The config is `runtime/configs/arduino.yaml` — it advertises what this node can do:
```yaml
device_id: arduino-01
device_type: arduino
accelerators: [cpu]
supported_ops: [echo, flag_risk, doc_event_detect]   # a real live node is what matters
privacy_ok: true
telemetry_mode: simulated
```

## 7. Run the agent → green tile

```bash
NEURAROUTE_BROKER=BROKER_IP python3 runtime/agent.py runtime/configs/arduino.yaml
```
**Expected, within ~2 s:**
- agent prints something like `arduino-01 up ... heartbeating`
- the **dashboard shows a green `arduino-01` tile**
- the **engine log** prints `device arduino-01 ALIVE`

Independent check (watch the raw heartbeats from any machine on the hotspot):
```bash
mosquitto_sub -h BROKER_IP -t neuraroute/heartbeat -v      # expect arduino-01 JSON every ~1.5 s
```
- **Agent runs but no tile / no ALIVE** → the agent connected to a **different broker** than the engine. Confirm both use the same `BROKER_IP`. Confirm `mosquitto_sub` above shows arduino-01 — if it does, the problem is the dashboard/engine side, not the board.
- **Tile appears then goes red after 3 s** → heartbeats stopped (agent crashed or Wi-Fi dropped). Check the agent's terminal for a traceback; re-run step 5.

## 8. (Optional) a real op on the board

Advertise one of these in `models:` so the scheduler can route real work here:
1. **`doc_event_detect`** — rule-based keyword flag (plan B, guaranteed). *This is enough — the demo needs a live node, not a big model.*
2. tiny **TFLite** op (stretch — only if everything else is green).
3. **`echo`** — last-resort plumbing op; still proves a real, routable node.

---

## Done when
- [ ] Green `arduino-01` tile, real heartbeats, on the projector
- [ ] It round-trips at least one dispatched op (dashboard shows a task landing on `arduino-01`)

## Fallback (§8 of the build plan)
| Plan A | Plan B | Plan C |
|---|---|---|
| Agent + tiny TFLite op | Agent + rule-based `doc_event_detect` (still a real live node) | **Simulated tile** (`python -m contracts.fake_device arduino-01`) — last resort, costs hardware points |

The demo needs a live green node, not a heroic debugging story. If the clock says fall back, fall back.
