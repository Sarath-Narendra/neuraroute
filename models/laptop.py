from pathlib import Path
import subprocess
import json


class LaptopModel:

    def __init__(self):

        self.model = "ai-hub-models/Qwen3-8B"
        prompt_file = (
            Path(__file__).parent.parent
            / "prompts"
            / "healthcare_system_prompt.txt"
        )

        with open(prompt_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def infer(self, patient_text):

        prompt = f"{self.system_prompt}\n\nPatient:\n{patient_text}"

        command = [
            "geniex",
            "infer",
            self.model,
            "--think=false",
            "-p",
            prompt
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode != 0:
            print(result.stderr)
            raise RuntimeError("GenieX inference failed")

        output = result.stdout

        decoder = json.JSONDecoder()

        # Find the last JSON object (the model's answer)
        last_brace = output.rfind("{")

        if last_brace == -1:
            raise Exception("No JSON object found.")

        obj, _ = decoder.raw_decode(output[last_brace:])

        return {
            "device": "laptop",
            "model": "Qwen3-8B",
            "runtime": "GenieX",
            "response": obj
        }