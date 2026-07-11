#!/usr/bin/env python3
"""tools/mock_llm.py — a tiny OpenAI-compatible /v1/chat/completions server.

Stands in for LM Studio (pc/phone tiers) and llama.cpp (arduino tier) during
development so the WHOLE system runs with zero model downloads and no GPU. It reads
the vitals out of NeuraRoute's triage prompt and returns clinically-plausible JSON
{"severity", "transcript"} — so the ladder, the watchdog, and the phone app can all
be demoed end-to-end on a laptop.

Swap it for the real thing at the venue by pointing the agents at LM Studio instead:
    NEURAROUTE_LOCAL_BASE_URL=http://<lm-studio-host>:1234/v1

Usage:
    python tools/mock_llm.py            # serves on :1234
    python tools/mock_llm.py 1234
"""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def triage_answer(prompt: str) -> str:
    vitals = {}
    m = re.search(r"CURRENT SENSOR READING:\s*(\{.*?\})", prompt, re.DOTALL)
    if m:
        try:
            vitals = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    name = "the patient"
    nm = re.search(r'"name":\s*"([^"]+)"', prompt)
    if nm:
        name = nm.group(1)

    def num(key, default):
        try:
            return float(vitals.get(key, default) or default)
        except (TypeError, ValueError):
            return default

    hr, spo2, temp, rr = num("hr", 80), num("spo2", 97), num("temp_c", 37.0), num("resp_rate", 16)

    problems = []
    if hr > 135 or hr < 40: problems.append(f"heart rate {hr:g} is critically abnormal")
    if spo2 < 85: problems.append(f"oxygen saturation {spo2:g}% is critically low")
    if temp > 40 or temp < 34: problems.append(f"temperature {temp:g}°C is critical")
    if rr > 30 or rr < 8: problems.append(f"respiratory rate {rr:g} is critical")

    concerns = []
    if 110 < hr <= 135: concerns.append(f"heart rate elevated at {hr:g}")
    if 85 <= spo2 < 93: concerns.append(f"SpO2 reduced at {spo2:g}%")
    if 38.2 < temp <= 40: concerns.append(f"fever of {temp:g}°C")
    if 22 < rr <= 30: concerns.append(f"raised respiratory rate {rr:g}")

    if problems:
        severity = "emergency"
        transcript = (
            f"{name} is in immediate danger: " + "; ".join(problems) + ". "
            "Compared with this patient's documented baseline these values represent an acute, "
            "life-threatening deterioration rather than expected variation. The pattern is consistent "
            "with acute decompensation and cannot wait for the morning round. Alert the on-call doctor "
            "immediately and stay with the patient. Prepare oxygen and IV access, and recheck vitals "
            "continuously rather than on the 20-second cycle. Escalate to transfer if there is no "
            "improvement within 10 minutes."
        )
    elif concerns:
        severity = "mild"
        transcript = (
            f"{name} shows early warning signs: " + "; ".join(concerns) + ". "
            "Against baseline this is a meaningful but not yet dangerous shift, most likely explained by "
            "their documented condition. Give the charted medication now and make the patient comfortable. "
            "Re-check vitals in 30 minutes and compare with tonight's trend, not just this single reading. "
            "Escalate to the doctor if any value crosses emergency thresholds or two readings in a row worsen."
        )
    else:
        severity = "normal"
        transcript = (
            f"{name}'s reading is within their expected range: HR {hr:g}, SpO2 {spo2:g}%, temperature "
            f"{temp:g}°C, respiratory rate {rr:g}. Compared with baseline there is no clinically significant "
            "drift, and nothing in the history changes that interpretation. No intervention is needed. "
            "Continue routine monitoring on the normal cycle and review the overnight trend at handover. "
            "Escalate only if a later reading breaches the patient's documented red flags."
        )
    return json.dumps({"severity": severity, "transcript": transcript})


def content_for(prompt: str) -> str:
    if "severity" in prompt and "SENSOR READING" in prompt:
        return triage_answer(prompt)
    return "Acknowledged."


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        user = ""
        for m in body.get("messages", []):
            if m.get("role") == "user":
                user = m.get("content", "")
        resp = {"choices": [{"message": {"role": "assistant", "content": content_for(user)}}]}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1234
    print(f"[mock_llm] OpenAI-compatible triage server on :{port}  (Ctrl-C to stop)", flush=True)
    try:
        ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n[mock_llm] stopped", flush=True)


if __name__ == "__main__":
    main()
