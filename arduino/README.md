# arduino/ — UNO Q failsafe display (serial monitor + LED)

The Arduino UNO Q is the **last tier of the ladder** and the **always-on watchdog**.

- **Linux side (QRB2210):** `runtime/agent.py` with `watchdog: true`. It holds every patient
  record locally (`records_path`), runs the tripwire + local SLM on *every* reading, raises
  `sos` alerts to the doctor's phone, and writes each verdict as a one line to the serial
  bridge (`serial_port` in `runtime/configs/arduino.yaml`).
- **STM32 side:** `neuraroute_monitor/neuraroute_monitor.ino` reads those lines and
  - echoes the full transcript to the **Arduino IDE Serial Monitor** (our bedside-display
    stand-in until an LCD is wired), and
  - drives the on-board **LED**: `EMERGENCY → fast blink`, `MILD → solid`, `NORMAL → off`.

## Bring-up (Sarath)
1. Flash `neuraroute_monitor.ino` to the STM32 via the Arduino IDE (UNO Q board package).
2. Confirm the Linux↔MCU bridge UART and set `serial_port` in `runtime/configs/arduino.yaml`
   to that device (e.g. `/dev/ttyAMA0`); baud is 115200 to match the sketch. Leave it `null`
   to mirror verdicts to the agent log only (works with no hardware).
3. Run the agent on the UNO Q: `python runtime/agent.py runtime/configs/arduino.yaml`
   (point `NEURAROUTE_BROKER` at the laptop hub).
4. Open the IDE Serial Monitor at 115200 — you'll see the SLM transcripts stream in, and the
   LED react, even with the laptop/cloud/PC/phone all down.

## Model on the UNO Q
The SLM is served locally as an OpenAI-compatible endpoint (llama.cpp `--server`); point the
agent at it with `NEURAROUTE_LOCAL_BASE_URL=http://localhost:1234/v1`. A ~0.5B Q4 model
(Qwen2.5-0.5B) fits comfortably in the 4 GB RAM; see `models/registry.py` (`arduino` entry).
