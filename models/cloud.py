import os
import json
from pathlib import Path

from dotenv import load_dotenv


class CloudModel:

    def __init__(self):

        load_dotenv()

        self.device = "cloud"
        self.runtime = "Groq"
        self.model = os.getenv("NEURAROUTE_CLOUD_MODEL", "llama-3.3-70b-versatile")

        # Lazy: build the Groq client on first infer, not at boot. A missing GROQ_API_KEY
        # (or the groq package not installed) must NOT crash the server on startup — the
        # cloud tier is meant to fail over DOWN the ladder when the cloud is unavailable.
        self._client = None

        prompt_file = (
            Path(__file__).parent.parent
            / "prompts"
            / "healthcare_system_prompt.txt"
        )

        with open(prompt_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GROQ_API_KEY not set — cloud tier fails over down the ladder"
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def infer(self, patient):

        response = self._get_client().chat.completions.create(

            model=self.model,

            temperature=0,

            messages=[
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": patient
                }
            ]
        )

        text = response.choices[0].message.content.strip()

        start = text.find("{")
        end = text.rfind("}")

        json_text = text[start:end + 1]

        return {
            "device": self.device,
            "runtime": self.runtime,
            "model": self.model,
            "response": json.loads(json_text)
        }