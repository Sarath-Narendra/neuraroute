"""
models/arduino.py — the UNO Q SLM tier (`arduino-01`), the LAST rung of the ladder.

>>> NOT BUILT YET — this is "the SLM part", the next piece of work. <<<

The other tiers are LLMs behind an OpenAI-compatible / Groq API; the Arduino UNO Q's
Dragonwing brain runs a *small* language model (Qwen2.5-0.5B-class, Q4, llama.cpp on CPU)
fully on-chip, as the failsafe when the cloud, PC, and phone are all gone.

Until this lands, the arduino tier stays on the shared local path (registry.py keeps
`arduino` as type=local -> llm_client -> NEURAROUTE_LOCAL_BASE_URL), so `arduino-01` is a
live, working tier via the dev mock / any llama.cpp server. Nothing here is wired into the
ladder yet.

To finish it, mirror models/phone.py: build an `ArduinoModel` that talks to the on-chip
llama.cpp server, add `servers/arduino_server.py` exposing POST /infer, then flip the
`arduino` entry in registry.py's VENUE_REGISTRY to type=infer_http with
NEURAROUTE_INFER_ARDUINO_URL (and add it to infer_up.sh + .env.example).
"""


class ArduinoModel:
    def __init__(self):
        raise NotImplementedError(
            "arduino SLM tier not built yet — this is the SLM part, next up. "
            "See the module docstring for how to finish it."
        )
