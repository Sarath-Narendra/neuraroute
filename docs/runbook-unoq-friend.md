# UNO Q Bring-up — Hand-off Runbook (for a friend on a separate PC)

**Hi! You don't need to know anything about this project.** Your one job: make a small
board called the **Arduino UNO Q** come alive as a device named **`arduino-01`** so it
shows up on the team's system. Follow these steps **in order**. After each step there's a
**"You should see"** line — if you see it, move on; if not, jump to **Troubleshooting** at
the bottom.

> **You will do two separate things:**
> - **PART A** — flash a tiny program onto the board's little screen/LED chip (Arduino IDE, all clicking).
> - **PART B** — turn the board's built-in mini-Linux computer into a live network device (typing commands).
>
> They are independent. If Part A gets stuck, skip to Part B — Part B is the important one.

> **Two placeholders you'll fill in as you go — write them on paper now:**
> - `BROKER_IP` = the IP address of **the PC running the broker** (either *your* PC in test mode, or Sarath's Surface at the venue). You'll get this in Part B, Step B1.
> - `BOARD_IP` = the UNO Q's own IP on Wi-Fi (only needed if you connect by SSH).

---

## What you need (checklist — get these before starting)

- [ ] The **Arduino UNO Q** board
- [ ] A **data-capable USB-C cable** (a charge-only cable will waste 30 min — use a known-good data cable)
- [ ] Your **PC** (Windows or Mac — both are fine)
- [ ] A **phone hotspot** (or Wi-Fi) that both your PC and the board can join. **Write down the Wi-Fi name + password.**
- [ ] Internet on your PC to download the Arduino IDE once

**Time budget:** Part A ≈ 20 min, Part B ≈ 30 min. If Part B isn't done in ~45 min, use the **Fallback** at the very bottom and tell Sarath.

---

# PART A — Flash the board's firmware (Arduino IDE, mostly clicking)

> This programs the board's **display/LED**. It does **not** need the internet-at-the-venue or the
> broker — you can do it any time. If you get stuck here for more than 15 min, **skip to Part B**;
> the demo still works without the LED.

### A1. Install the Arduino IDE on your PC
1. Open a browser → go to **https://www.arduino.cc/en/software**
2. Download **Arduino IDE 2.x** for your OS (Windows or macOS).
3. Install it (Windows: run the `.exe` and click through; Mac: drag Arduino to Applications).
4. Open the Arduino IDE.

**You should see:** the Arduino IDE window open, with a big code area in the middle.

### A2. Add the UNO Q board support
1. In the IDE, open **Tools → Board → Boards Manager…** (a search box appears on the left).
2. In that search box, type **`UNO Q`**.
3. Find the **Arduino UNO Q** entry → click **Install**. Wait for it to finish (progress bar at the bottom).

**You should see:** the entry now says **"INSTALLED"**.

### A3. Get the program file onto your PC
You need the file `neuraroute_monitor.ino` from the project. Easiest way:
1. Ask Sarath for the repo, or in a browser open the GitHub repo:
   **https://github.com/Sarath-Narendra/neuraroute**
2. Click the green **Code** button → **Download ZIP** → unzip it on your Desktop.
3. The file you need is inside the unzipped folder at:
   `neuraroute/arduino/neuraroute_monitor/neuraroute_monitor.ino`

**You should see:** a folder `neuraroute_monitor` containing `neuraroute_monitor.ino`.

### A4. Open the program
1. In the Arduino IDE: **File → Open…**
2. Navigate to and select `arduino/neuraroute_monitor/neuraroute_monitor.ino`.

**You should see:** code appear in the editor, with a tab named **neuraroute_monitor**.

### A5. Plug in the board
1. Connect the UNO Q to your PC with the **data** USB-C cable.
2. Wait ~10 seconds.

**You should see:** a power light on the board.

### A6. Pick the board and port
1. **Tools → Board →** select **Arduino UNO Q**.
2. **Tools → Port →** select the port that appeared when you plugged in
   (Windows: a `COM3`/`COM4`-style entry; Mac: something like `/dev/cu.usbmodem…`).

**You should see:** both Board and Port now show a value (not "unknown").

### A7. Upload
1. Click the **→ (Upload)** arrow button in the top-left of the IDE.
2. Wait — it compiles then uploads (30–60 s).

**You should see:** **"Done uploading"** at the bottom, with no red error text.

### A8. Confirm it's running
1. Open **Tools → Serial Monitor**.
2. In the Serial Monitor, set the baud dropdown (bottom-right) to **115200**.

**You should see:** a line like **`== NeuraRoute UNO Q monitor ready ==`**.

> ✅ **Part A done.** The LED won't react to anything yet — it waits for messages that come
> later (optional Part B, Step B12). The "ready" banner is all you need here.
>
> ❌ **If A6 shows no port / A7 errors:** try a different **data** USB-C cable and a different USB
> port, then repeat A5–A7. Still stuck after 15 min → **skip to Part B**.

---

# PART B — Bring the board's Linux side online as `arduino-01`

> The UNO Q secretly contains a tiny **Linux computer** (Qualcomm side). We're going to
> log into it, join the Wi-Fi, and run one program that makes it a live network device.

### B1. Get the `BROKER_IP` (the PC everything talks to)

There are two situations — pick the one that matches today:

**Situation 1 — You're testing alone on your own PC (do this first, to prove the board works):**
Your PC will be the broker. Get **your PC's** IP on the hotspot:
- **Windows:** open **Command Prompt**, run:
  ```
  ipconfig
  ```
  Find your Wi-Fi adapter's **IPv4 Address** (e.g. `192.168.137.1` or `192.168.43.100`).
- **Mac:** open **Terminal**, run:
  ```
  ipconfig getifaddr en0
  ```

**Situation 2 — At the venue with the team:** ask **Sarath for the Surface's IP** — that's the broker.

➡️ **Write the number down as `BROKER_IP`.** You'll type it several times below.

### B2. Install the broker + test tools ON YOUR PC *(only needed for Situation 1 — testing alone)*
> Skip this whole step if you're at the venue using Sarath's Surface as the broker.

This gives your PC a "message post office" the board can connect to, plus a tool to watch messages.

- **Windows:**
  1. Download the Mosquitto Windows installer from **https://mosquitto.org/download/** and run it (accept defaults).
  2. It installs to `C:\Program Files\mosquitto`.
- **Mac:**
  ```
  brew install mosquitto
  ```
  (If you don't have Homebrew, install it from **https://brew.sh** first.)

**You should see:** the install finishes with no errors.

### B3. Start the broker ON YOUR PC *(Situation 1 only)*
Open a terminal on your PC and run it so it listens for everyone on the hotspot:
- **Windows** (in Command Prompt):
  ```
  "C:\Program Files\mosquitto\mosquitto.exe" -v -p 1883
  ```
- **Mac:**
  ```
  /opt/homebrew/opt/mosquitto/sbin/mosquitto -v -p 1883
  ```

**You should see:** lines like `mosquitto version ... running`. **Leave this window open** — it must stay running. Open a **new** terminal for the next steps.

> ⚠️ **Windows firewall:** the first time, Windows may pop up "Allow mosquitto to communicate?" —
> click **Allow access** (tick Private networks). If you didn't see it, you may need to manually
> open **inbound TCP port 1883** in Windows Defender Firewall. This is the #1 reason the board
> "can't connect" later.

### B4. Power the board and wait for its Linux to boot
1. Keep the board plugged into your PC by USB-C (or a USB power brick).
2. **Wait 60–90 seconds** — the Linux side boots on its own.

**You should see:** after ~90 s the board behaves like a small computer (we log in next).

### B5. Get a terminal (shell) ON THE BOARD'S LINUX SIDE
Pick the easiest option that works:

- **Option A — Arduino App Lab (recommended, GUI):** install **Arduino App Lab** on your PC
  (from https://www.arduino.cc), open it, and open the board's **Linux terminal** panel.
- **Option B — SSH:** if the board is already on Wi-Fi and you know its `BOARD_IP`:
  ```
  ssh <username>@BOARD_IP
  ```
  (Ask Sarath for the board's username/password if unsure.)

**You should see:** a text prompt ending in `$`. Confirm you're on the right (Linux) side:
```bash
uname -a
```
**You should see:** a line containing **`Linux`** and **`aarch64`**.
- If it does **not** say `aarch64`, you're on the wrong console (that's the small chip, not the
  Linux computer). Use App Lab's **Linux** terminal, not the Arduino Serial Monitor.

> **Every command from here down is typed INTO THE BOARD'S terminal**, not your PC's — unless it says "on your PC".

### B6. Join the board to the same Wi-Fi / hotspot
In the board's terminal:
```bash
nmcli dev wifi connect "WIFI_NAME_HERE" password "WIFI_PASSWORD_HERE"
```
Then confirm:
```bash
nmcli -t -f active,ssid dev wifi
```
**You should see:** a line starting with `yes:` followed by your Wi-Fi name.

### B7. Prove the board can REACH the broker PC
Still in the board's terminal (replace `BROKER_IP` with your number from B1):
```bash
ping -c 3 BROKER_IP
```
**You should see:** `3 packets transmitted, 3 received, 0% packet loss`.
- **If it fails (100% loss):** the board and the broker PC are not talking. Do NOT continue —
  fix networking first: same Wi-Fi? firewall open on the PC (see B3 warning)? Re-check B1's IP.

### B8. Install Python + the network library ON THE BOARD
In the board's terminal:
```bash
python3 --version
```
- If Python is missing or below 3.9:
  ```bash
  sudo apt update && sudo apt install -y python3 python3-pip
  ```
Then install the libraries:
```bash
pip3 install paho-mqtt pyyaml requests
```
- If you see **"externally-managed-environment"**, run it again with this flag:
  ```bash
  pip3 install --break-system-packages paho-mqtt pyyaml requests
  ```

**You should see:** `Successfully installed paho-mqtt ...` (or "already satisfied").

### B9. Prove the board can TALK to the broker (not just ping it)
In the board's terminal (replace `BROKER_IP`):
```bash
python3 -c "import paho.mqtt.client as m; c=m.Client(m.CallbackAPIVersion.VERSION2); c.connect('BROKER_IP',1883); print('CONNECTED')"
```
**You should see:** exactly **`CONNECTED`**.
- **`ConnectionRefusedError` / it hangs then errors:** broker isn't reachable. Go back to B3
  (is the broker running?) and the B3 firewall warning. This is networking, not the code.

### B10. Get the project code ONTO THE BOARD
In the board's terminal:
```bash
git clone https://github.com/Sarath-Narendra/neuraroute.git
cd neuraroute
```
- If `git` is missing: `sudo apt install -y git` then re-run the clone.

**You should see:** a `neuraroute` folder, and after `cd` your prompt is inside it.

### B11. RUN the device — this is the moment it goes live
In the board's terminal (still inside the `neuraroute` folder; replace `BROKER_IP`):
```bash
NEURAROUTE_BROKER=BROKER_IP \
NEURAROUTE_LOCAL_BASE_URL=http://BROKER_IP:1234/v1 \
  python3 runtime/agent.py runtime/configs/arduino.yaml
```
> The `NEURAROUTE_LOCAL_BASE_URL` line points the board's "brain" at a model server. In simple
> testing you can leave it as shown — the board still goes live and the emergency alarm still works
> even if that model server isn't running (the alarm uses a hard number rule, not the model).

**You should see (within ~2 seconds):**
- the program prints something like `arduino-01 ... heartbeating`
- **it keeps running** (don't close this window — the board is "alive" only while this runs)

### B12. VERIFY it's really alive (do this on YOUR PC)
Open a **new terminal on your PC** and watch the heartbeats (replace `BROKER_IP`):
- **Windows:**
  ```
  "C:\Program Files\mosquitto\mosquitto_sub.exe" -h BROKER_IP -t neuraroute/heartbeat -v
  ```
- **Mac:**
  ```
  mosquitto_sub -h BROKER_IP -t neuraroute/heartbeat -v
  ```

**You should see:** a JSON line mentioning **`arduino-01`** appear **every ~1.5 seconds**.

> 🎉 **THAT is success.** `arduino-01` is a live device on the network. Tell Sarath:
> **"arduino-01 is heartbeating on BROKER_IP."** The team's phone app will now show it as a green tile.

---

## OPTIONAL — nice-to-haves (only if B12 works and you have spare time)

### Optional 1 — The on-board "brain" (real model answers)
The board can answer with a real tiny AI model using **llama.cpp**. This is advanced and NOT
required (the emergency alarm works without it). If Sarath asks for it:
1. On the board, run a small llama.cpp server (a ~0.5B Q4 model) on port `1234`.
2. Point the agent at it: set `NEURAROUTE_LOCAL_BASE_URL=http://localhost:1234/v1` in the B11 command.
If you don't have a model ready, just leave B11 as-is — the tier still works with the team's mock brain.

### Optional 2 — Make the LED react (needs Part A done)
1. Find the wire between Linux and the little chip:
   ```bash
   ls /dev/ttyAMA* /dev/ttyHS* 2>/dev/null
   ```
   (usually `/dev/ttyAMA0`).
2. On the board, edit `runtime/configs/arduino.yaml` and change the last line from
   `serial_port: null` to `serial_port: /dev/ttyAMA0`.
3. Re-run the B11 command.
4. Ask Sarath to send a **Critical** reading. On the Arduino IDE **Serial Monitor** (baud 115200)
   you should see an `EMERGENCY` line and the on-board **LED fast-blinks**.
   (Normal reading → LED off; mild → solid on.)

---

## Troubleshooting (find your symptom)

| What went wrong | What to do |
|---|---|
| **Part A: no Port shows / Upload fails** | Use a different **data** USB-C cable + different USB port. If still stuck 15 min, skip Part A — it's optional. |
| **B5: `uname` doesn't say `aarch64`** | You're on the wrong console. Use Arduino **App Lab → Linux terminal**, not the Serial Monitor. |
| **B7: `ping` fails (100% loss)** | Board and PC not on the **same** hotspot, OR the PC's firewall blocks it. Rejoin Wi-Fi (B6); allow inbound **TCP 1883** on the PC (B3 warning). |
| **B9: `ConnectionRefusedError`** | Broker isn't running or is blocked. On your PC restart the broker (B3) and allow it through the firewall. |
| **B11: crashes with `ModuleNotFound`** | A library didn't install. Re-run B8 (add `--break-system-packages` if it complained). |
| **B12: no `arduino-01` line appears** | The board's agent connected to a **different** broker than you're watching. Confirm the **same `BROKER_IP`** in B11 and B12. |
| **Tile/heartbeat appears then stops after 3 s** | The agent crashed or Wi-Fi dropped. Look at the board terminal (B11) for a red error; re-run B9 then B11. |

---

## Fallback (if the board just won't come up)

Don't burn more than ~45 minutes. If `arduino-01` isn't heartbeating by then, tell Sarath —
the team can host `arduino-01` on a laptop instead and the demo is unaffected. **Getting the board
alive (B12) is the win; the LED and the on-board model are bonuses.**

---

## One-line summary to send Sarath when done
> ✅ `arduino-01` heartbeating on `BROKER_IP` — [Part A LED: done / skipped] — [on-board model: yes / no].
