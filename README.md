# NeuraRoute

**An AI safety net for a night nurse who is watching many patients alone — one that keeps working even when the internet, the laptop, and the phone all fail.**

---

## What is this?

Picture a small rural health center at night. One nurse is looking after ten patients. Every
few seconds, a device reads each patient's vital signs — heart rate, blood-oxygen (SpO₂),
temperature, and breathing rate — and sends them to an AI to be checked.

The AI reads the numbers, compares them against that patient's medical history, and decides
how worried we should be:

- **normal** — nothing to do
- **mild** — keep an eye on it
- **emergency** — the nurse (and the doctor) must be told *right now*

The hard part is not the AI. The hard part is **staying alive when things break.** Rural
internet drops. Laptops die. Phones run out of battery. NeuraRoute is built so that the
patient is still being watched no matter what fails.

### The "ladder" — always use the best brain that is still reachable

NeuraRoute keeps a ranked list of AI "brains." For every reading, it uses the **first one on
the list that is currently alive**, and automatically slides down to the next one when
something goes offline:

| Order | Brain | Runs when… |
|:---:|---|---|
| 1 | **Cloud AI** (the smartest, knows full patient history) | the internet is working |
| 2 | **Laptop AI** | internet is down, but the laptop is on |
| 3 | **Phone AI** | the laptop is down too |
| 4 | **Tiny chip AI** (a small model on an Arduino board) | everything else is gone |

As each brain drops away, the system still works — just with a smaller, simpler AI. This is
called **graceful degradation**: it gets weaker step by step instead of switching off all at
once.

### The always-on alarm

Separately from the ladder, the tiny Arduino chip runs a **watchdog** that checks *every*
reading on its own. If a value crosses a hard danger line (for example heart rate above 135,
or SpO₂ below 85), or the small on-chip AI spots a clear emergency, it **sends a real
notification straight to the doctor's phone** — even if the internet, the laptop, the phone,
and the main program have all failed.

> Built for the **Snapdragon Multiverse Hackathon** (Bengaluru, July 2026). You can run the
> **entire system on one laptop with no cloud account and no special AI hardware** — the AI
> parts are replaced by a small built-in "mock" so nothing needs to be downloaded.

---

## Before you start (prerequisites)

Install these once:

| Tool | What it's for | Get it |
|---|---|---|
| **Python 3.11+** | runs the main program | [python.org](https://www.python.org/downloads/) — on Windows: `winget install Python.Python.3.12` |
| **Mosquitto** | the "post office" the parts use to talk to each other | Windows: `winget install EclipseFoundation.Mosquitto` · macOS: `brew install mosquitto` · Linux: `apt install mosquitto` |
| **Node.js 20+** *(only for the phone app)* | builds the doctor's phone screen | [nodejs.org](https://nodejs.org) |
| **Expo Go** *(only for the phone app)* | the app you open on your phone to see the live screen | App Store / Google Play |

---

## Install

Run these once, in a terminal, inside the folder where you want the project.

**Windows (PowerShell):**

```powershell
git clone https://github.com/Sarath-Narendra/neuraroute.git
cd neuraroute

py -3.12 -m venv .venv               # create an isolated Python space
.venv\Scripts\Activate.ps1           # turn it on
pip install -r requirements.txt      # install the program's needs

cd mobile; npm install; cd ..        # phone-app needs (optional)
```

**macOS / Linux:**

```bash
git clone https://github.com/Sarath-Narendra/neuraroute.git
cd neuraroute

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd mobile && npm install && cd ..
```

---

## Run it (the whole system, on one machine)

This starts everything at once — the "post office," a stand-in AI (so nothing needs
downloading), the main program, and all four AI brains on the ladder.

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
```

**macOS / Linux:**

```bash
./scripts/dev_up.sh
```

When it's up, the main program is listening at **http://localhost:8080**.

### Try it — send a patient reading

Send a made-up **critical** reading and watch the system flag it as an emergency and fire the
alarm.

**Windows (PowerShell):**

```powershell
curl -Method POST http://localhost:8080/request -ContentType application/json `
     -Body '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'
```

**macOS / Linux:**

```bash
curl -XPOST localhost:8080/request -H 'Content-Type: application/json' \
     -d '{"patient_id":"P-03","vitals":{"hr":176,"spo2":79,"temp_c":37,"resp_rate":32}}'
```

### Try it — break a brain and watch it recover

"Kill" the top brain on the ladder, then send another reading. NeuraRoute will notice and
automatically route the next reading to the brain one step down — live.

**Windows (PowerShell):**

```powershell
powershell -File scripts\kill_device.ps1 cloud-01
```

**macOS / Linux:**

```bash
./scripts/kill_device.sh cloud-01
```

### Stop everything

**Windows (PowerShell):**

```powershell
powershell -File scripts\dev_down.ps1
```

**macOS / Linux:** press `Ctrl-C` in the window running the stack.

---

## The doctor's phone app (optional)

The phone app shows the ten patients, which AI brain is currently in use, and pops up a real
alert on every emergency.

1. Make sure your phone is on the **same Wi-Fi / hotspot** as the computer.
2. Start it:

   ```bash
   cd mobile
   npx expo start
   ```

3. Open **Expo Go** on your phone and scan the code that appears.

The app finds the computer automatically. If it can't, you can type the computer's address
into the app by hand.

---

## Using real AI models (optional, advanced)

By default the system uses a built-in stand-in AI so anyone can run it. When you have real
models and want to use them, NeuraRoute can point each brain at a real model server instead —
this is called **venue mode**. The rest of the system (the ladder, the failover, the phone
app, the alarm) does not change; only *where the thinking happens* changes.

See **`scripts/README.md`** and **`.env.example`** for the exact settings. In short: copy
`.env.example` to `.env`, fill in your keys, and start the model servers with `infer_up.ps1`
(Windows) or `infer_up.sh` (macOS / Linux) before bringing the stack up.

---

## What's in this repo

A quick map, so you know where to look:

```
neuraroute/
  engine/      the main program — runs the ladder and decides which brain handles each reading
  models/      the AI logic: reads vitals, compares to history, returns a severity
  servers/     the real per-device model servers (used only in "venue mode")
  runtime/     each AI "brain" on the ladder, plus its settings
  mobile/      the doctor's phone app
  arduino/     the tiny-chip program: the always-on alarm and status light
  contracts/   the agreed message formats every part uses to talk
  prompts/     the instructions given to the AI
  tools/       stand-in AIs so you can run everything with no downloads
  scripts/     one-command start / stop / failover helpers
  data/        the sample list of ten patients
  docs/        setup notes for the real hardware
```

---

## Technical architecture

> _Detailed technical architecture — component diagram, message flow, and the message
> formats — will be added here._

---

## The team

Built by:

- **Sankarasetty Jaya Abhiram**
- **Sarath Narendra Kuppala**
- **Gowtham Sai Kalyan**
- **Reddy Eswar Anush**

---

## License

Released under the [MIT License](LICENSE). All the tools it is built on are open-source.
