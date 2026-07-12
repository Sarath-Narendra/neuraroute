"""
models/registry.py

Which model + adapter runs `triage` on each tier. Pick the registry with one env var:

    NEURAROUTE_REGISTRY=dev     (default) — everything local/mock, runs on one laptop, no
                                 real models. Local tiers hit NEURAROUTE_LOCAL_BASE_URL
                                 (LM Studio / tools/mock_llm.py); cloud is the canned mock.

    NEURAROUTE_REGISTRY=venue   — the real inference module (the /infer servers):
                                 laptop -> GenieX/Qwen  at NEURAROUTE_INFER_LAPTOP_URL,
                                 cloud  -> Groq/Llama-70B at NEURAROUTE_INFER_CLOUD_URL,
                                 phone  -> llama.cpp SLM at NEURAROUTE_INFER_PHONE_URL.
                                 arduino stays local until its SLM /infer server lands.

`type` drives run_model's routing: "infer_http" -> models/infer_client (POST /infer),
"cloud" -> models/cloud_adapter (canned mock), anything else -> the local op via llm_client.
"""
import os

# The inference servers' endpoints (override per venue/network).
INFER_LAPTOP_URL = os.environ.get("NEURAROUTE_INFER_LAPTOP_URL", "http://localhost:8000/infer")
INFER_CLOUD_URL = os.environ.get("NEURAROUTE_INFER_CLOUD_URL", "http://localhost:8001/infer")
INFER_PHONE_URL = os.environ.get("NEURAROUTE_INFER_PHONE_URL", "http://localhost:8002/infer")


# ==========================================================
# dev — one laptop, no real models (local mock / LM Studio)
# ==========================================================
DEV_REGISTRY = {
    "surface":  {"triage": {"model": "Phi-3 (LM Studio)", "adapter": "llm_client", "type": "local"}},
    "phone":    {"triage": {"model": "Phi-3 (LM Studio)", "adapter": "llm_client", "type": "local"}},
    "arduino":  {"triage": {"model": "Qwen2.5-0.5B (llama.cpp)", "adapter": "llm_client", "type": "local"}},
    "cloud":    {"triage": {"model": "gpt-4o-mini (mock)", "adapter": "openai_cloud", "type": "cloud"}},
}


# ==========================================================
# venue — the real AI-inference module (Eswar's /infer servers)
# ==========================================================
VENUE_REGISTRY = {
    "surface":  {"triage": {"model": "Qwen3.5-2B / GenieX", "adapter": "infer_http",
                            "type": "infer_http", "infer_url": INFER_LAPTOP_URL}},
    "phone":    {"triage": {"model": "Gemma 3 1B / Ollama", "adapter": "infer_http",
                            "type": "infer_http", "infer_url": INFER_PHONE_URL}},
    # arduino /infer server is the SLM part — still pending; keep it on the local path so
    # arduino-01 stays a live tier via the dev mock / any llama.cpp server (see models/arduino.py).
    "arduino":  {"triage": {"model": "local SLM (llama.cpp)", "adapter": "llm_client", "type": "local"}},
    "cloud":    {"triage": {"model": "llama-3.3-70b / Groq", "adapter": "infer_http",
                            "type": "infer_http", "infer_url": INFER_CLOUD_URL}},
}


_REGISTRIES = {"dev": DEV_REGISTRY, "venue": VENUE_REGISTRY}
ACTIVE_REGISTRY = _REGISTRIES.get(os.environ.get("NEURAROUTE_REGISTRY", "dev"), DEV_REGISTRY)


# Contract device_ids (contracts/topics.py + runtime/configs/*.yaml) -> friendly registry keys,
# so the agent can pass its raw device_id ("pc-01") straight into run_model(). Keys map to
# themselves too, so callers passing "surface"/"cloud" keep working.
DEVICE_ALIASES = {
    "pc-01": "surface", "surface": "surface",
    "phone-01": "phone", "phone": "phone",
    "arduino-01": "arduino", "arduino": "arduino", "unoq": "arduino",
    "cloud-01": "cloud", "cloud": "cloud",
}


def get_model_config(device: str, task: str) -> dict:
    """Model config for a device+task. Accepts a registry key ("surface") or a contract
    device_id ("pc-01"); the latter resolves via DEVICE_ALIASES."""
    key = DEVICE_ALIASES.get(device, device)
    if key not in ACTIVE_REGISTRY:
        raise ValueError(f"Unsupported device: {device}")
    if task not in ACTIVE_REGISTRY[key]:
        raise ValueError(f"Task '{task}' not supported on device '{device}'")
    return ACTIVE_REGISTRY[key][task]
