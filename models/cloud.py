import os
import json

from dotenv import load_dotenv
from groq import Groq


class CloudModel:

    def __init__(self):

        load_dotenv()

        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        self.device = "cloud"
        self.model = "llama-3.3-70b-versatile"

        with open(
            "prompts/healthcare_system_prompt.txt",
            "r",
            encoding="utf-8"
        ) as f:
            self.system_prompt = f.read()

    def infer(self, patient):

        response = self.client.chat.completions.create(

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
            "runtime": "Groq",
            "model": self.model,
            "response": json.loads(json_text)
        }