#!/usr/bin/env python3
"""tools/mock_infer.py — a stand-in for the inference module's `POST /infer` server.

Speaks Eswar's EXACT contract (request {"patient": text}; response {device,runtime,model,
response{summary,symptoms,possible_conditions,severity,emergency,confidence,next_action,
requires_cloud}}) so we can verify the engine<->/infer bridge end-to-end with no real
models. Reads the vitals out of the patient text and returns a clinically-plausible verdict.

Usage (mimic the two real servers):
    python tools/mock_infer.py 8000 laptop GenieX Qwen3.5-2B
    python tools/mock_infer.py 8001 cloud  Groq   llama-3.3-70b-versatile
"""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEVICE = sys.argv[2] if len(sys.argv) > 2 else "laptop"
RUNTIME = sys.argv[3] if len(sys.argv) > 3 else "GenieX"
MODEL = sys.argv[4] if len(sys.argv) > 4 else "Qwen3.5-2B"


def num(text, key, default):
    # Read the CURRENT reading, not the baseline. infer_client._describe() renders
    # "baseline vitals: hr 64, ..." BEFORE "CURRENT sensor reading: hr 176, ...", so a
    # naive first-match grabs the baseline and every verdict looks normal. Scope the
    # search to the text after the CURRENT marker when it's present.
    marker = re.search(r"current sensor reading", text, re.IGNORECASE)
    scope = text[marker.start():] if marker else text
    m = re.search(rf"{key}\s+(\d+(?:\.\d+)?)", scope, re.IGNORECASE)
    return float(m.group(1)) if m else default


def infer(patient_text: str) -> dict:
    hr = num(patient_text, "hr", 80)
    spo2 = num(patient_text, "spo2", 97)
    temp = num(patient_text, "temp_c", 37.0)
    rr = num(patient_text, "resp_rate", 16)

    symptoms, conditions = [], []
    emergency = hr > 135 or hr < 40 or spo2 < 85 or temp > 40 or rr > 30
    if hr > 110: symptoms.append("tachycardia")
    if spo2 < 93: symptoms.append("hypoxia"); conditions.append("respiratory compromise")
    if temp > 38.2: symptoms.append("fever"); conditions.append("infection")
    if rr > 22: symptoms.append("tachypnea")

    if emergency:
        severity, action = "high", "Alert the doctor immediately; prepare oxygen and IV access."
    elif symptoms:
        severity, action = "medium", "Give charted medication and recheck vitals in 30 minutes."
    else:
        severity, action = "low", "Continue routine monitoring."

    summary = (f"Reading shows HR {hr:g}, SpO2 {spo2:g}%, temp {temp:g}C, resp {rr:g}. "
               + ("Acute deterioration versus baseline — immediate attention required."
                  if emergency else
                  "Early warning signs; monitor closely." if symptoms else
                  "Within the patient's expected range."))
    return {
        "summary": summary,
        "symptoms": symptoms,
        "possible_conditions": conditions,
        "severity": severity,
        "emergency": emergency,
        "confidence": 0.82,
        "next_action": action,
        "requires_cloud": severity != "low" and DEVICE == "laptop",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        out = {"device": DEVICE, "runtime": RUNTIME, "model": MODEL,
               "response": infer(str(body.get("patient", "")))}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"[mock_infer] {DEVICE} /infer ({RUNTIME}/{MODEL}) on :{port}", flush=True)
    try:
        ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n[mock_infer] stopped", flush=True)


if __name__ == "__main__":
    main()
