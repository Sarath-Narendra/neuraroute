"""
models/phone.py

Phone tier (`phone-01`) inference — the THIRD rung of the connectivity ladder, used
when both the cloud and the PC are down. Mirrors laptop.py / cloud.py: a self-contained
model wrapper that `servers/phone_server.py` exposes at `POST /infer`, so the phone can
run its own `/infer` server (Termux on the OnePlus, or a laptop hosting the tier — see
docs/runbook-phone.md Plan B) decoupled from the engine.

On the OnePlus 15 the phone runs a small Q4 GGUF model (e.g. Qwen3-1.7B, per the Android
demo's model_list.json) behind an OpenAI-compatible llama.cpp / LM Studio server. This
wrapper is a thin bridge to that server; point it with NEURAROUTE_PHONE_LLM_URL. The
returned shape is the inference module's frozen `/infer` schema, identical to laptop/cloud:

    {"device","runtime","model","response": {summary,symptoms[],possible_conditions[],
                                             severity,emergency,confidence,next_action,
                                             requires_cloud}}

Env:
    NEURAROUTE_PHONE_LLM_URL   OpenAI-compatible base URL (default http://localhost:1234/v1)
    NEURAROUTE_PHONE_MODEL     model name to request (default "Qwen3-1.7B")
    NEURAROUTE_PHONE_TIMEOUT_S per-call timeout (default 60s — small models on-device are slow)
"""
import os
import json
from pathlib import Path

import requests


class PhoneModel:

    def __init__(self):

        self.device = "phone"
        self.runtime = "llama.cpp"
        self.base_url = os.environ.get(
            "NEURAROUTE_PHONE_LLM_URL", "http://localhost:1234/v1"
        ).rstrip("/")
        self.model = os.environ.get("NEURAROUTE_PHONE_MODEL", "Qwen3-1.7B")
        self.timeout_s = float(os.environ.get("NEURAROUTE_PHONE_TIMEOUT_S", "60.0"))

        prompt_file = (
            Path(__file__).parent.parent
            / "prompts"
            / "healthcare_system_prompt.txt"
        )

        with open(prompt_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def infer(self, patient):

        url = self.base_url + "/chat/completions"

        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": patient
                }
            ]
        }

        resp = requests.post(url, json=body, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()

        text = data["choices"][0]["message"]["content"].strip()

        # Small local models routinely wrap the JSON in prose; take the outermost object.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise RuntimeError("No JSON object found in phone model output.")

        obj = json.loads(text[start:end + 1])

        return {
            "device": self.device,
            "runtime": self.runtime,
            "model": self.model,
            "response": obj
        }
