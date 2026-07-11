/*
 * NeuraRoute — Arduino UNO Q, STM32 side (the "serial monitor + LED" failsafe display).
 *
 * ARCHITECTURE
 *   The SLM watchdog runs on the UNO Q's Linux side (Qualcomm QRB2210), inside
 *   runtime/agent.py. On every vitals reading it runs the tripwire + the local SLM and
 *   writes a one-line verdict to a serial device (config `serial_port` in
 *   runtime/configs/arduino.yaml). That line arrives here on the STM32 over the
 *   Linux<->MCU UART bridge. This sketch:
 *     1. echoes the full transcript to the USB Serial Monitor in the Arduino IDE
 *        (our stand-in for a bedside display until we wire an LCD), and
 *     2. drives the on-board LED by severity:
 *          EMERGENCY -> fast blink   MILD -> solid on   NORMAL -> off
 *
 * LINE FORMAT written by the Linux side (see DeviceAgent._serial_write):
 *     [P-03] EMERGENCY (watchdog): <transcript...>
 *     !!! EMERGENCY P-03: tripwire: hr 176 > 135 bpm; spo2 79 < 85 %
 *
 * WIRING NOTE
 *   `LINK` is the UART from the Linux side. On the UNO Q use the bridge UART the Linux
 *   agent opens (commonly exposed as Serial1); on a plain dev board you can jumper a
 *   USB-UART adapter to pins 0/1 and set serial_port to that adapter. Baud must match
 *   the agent's 115200. If your board has only one hardware UART, flip USE_SOFTWARE_LINK.
 */

#define LINK        Serial1        // UART carrying verdicts from the Linux/SLM side
#define LINK_BAUD   115200
#define MONITOR     Serial         // USB CDC -> Arduino IDE Serial Monitor
#define MONITOR_BAUD 115200

#ifndef LED_BUILTIN
#define LED_BUILTIN 13
#endif

enum Severity { SEV_NONE, SEV_NORMAL, SEV_MILD, SEV_EMERGENCY };
static Severity current = SEV_NONE;

static char lineBuf[512];
static size_t lineLen = 0;

// non-blocking blink state for the EMERGENCY pattern
static unsigned long lastToggle = 0;
static bool ledOn = false;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  MONITOR.begin(MONITOR_BAUD);
  LINK.begin(LINK_BAUD);
  while (!MONITOR && millis() < 3000) { /* wait briefly for USB host */ }
  MONITOR.println(F("== NeuraRoute UNO Q monitor ready =="));
  MONITOR.println(F("Waiting for triage verdicts from the SLM watchdog..."));
}

Severity classify(const char* s) {
  // case-sensitive match on the uppercase keywords the agent emits
  if (strstr(s, "EMERGENCY")) return SEV_EMERGENCY;
  if (strstr(s, "MILD"))      return SEV_MILD;
  if (strstr(s, "NORMAL"))    return SEV_NORMAL;
  return SEV_NONE;
}

void handleLine(const char* line) {
  if (line[0] == '\0') return;

  // 1) mirror the full transcript to the IDE Serial Monitor
  MONITOR.println(line);

  // 2) update the LED severity state (keep the last known if this line has no keyword)
  Severity sev = classify(line);
  if (sev != SEV_NONE) {
    current = sev;
    switch (current) {
      case SEV_EMERGENCY: MONITOR.println(F("   >> LED: FAST BLINK (emergency)")); break;
      case SEV_MILD:      MONITOR.println(F("   >> LED: SOLID (mild)"));
                          digitalWrite(LED_BUILTIN, HIGH); break;
      case SEV_NORMAL:    MONITOR.println(F("   >> LED: OFF (normal)"));
                          digitalWrite(LED_BUILTIN, LOW); break;
      default: break;
    }
  }
}

void updateLed() {
  if (current == SEV_EMERGENCY) {
    unsigned long now = millis();
    if (now - lastToggle >= 120) {     // ~4 Hz panic blink
      lastToggle = now;
      ledOn = !ledOn;
      digitalWrite(LED_BUILTIN, ledOn ? HIGH : LOW);
    }
  }
  // MILD (solid) and NORMAL (off) are set once in handleLine
}

void loop() {
  while (LINK.available()) {
    char c = (char)LINK.read();
    if (c == '\n' || c == '\r') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
    } else if (lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    } else {
      // overflow guard: flush what we have
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
    }
  }
  updateLed();
}
