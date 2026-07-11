"""
models/registry.py

Central Model Registry — which model + adapter runs `triage` on each tier.

DEV_REGISTRY      -> your own laptop (everything hits the local mock / LM Studio)
QUALCOMM_REGISTRY -> the hackathon hardware (Surface X Elite, OnePlus, Uno Q, AI Cloud)

Switch by changing ONE line: ACTIVE_REGISTRY = QUALCOMM_REGISTRY

The cloud tier's entry has type "cloud" — run_model() routes those calls through
cloud_adapter (GPT). Everything else is local via llm_client (any OpenAI-compatible
server: LM Studio on the laptops/phone, llama.cpp --server on the Uno Q).
"""

# ==========================================================
# LOCAL DEVELOPMENT (Your Laptop)
# ==========================================================

DEV_REGISTRY = {

    "surface": {
        "triage": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "phone": {
        "triage": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "arduino": {
        "triage": {
            "model": "Qwen2.5-0.5B (llama.cpp)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "cloud": {
        "triage": {
            "model": "gpt-4o-mini",
            "adapter": "openai_cloud",
            "type": "cloud"
        }
    }
}


# ==========================================================
# QUALCOMM HACKATHON HARDWARE
# ==========================================================

QUALCOMM_REGISTRY = {

    "surface": {
        "triage": {
            "model": "Gemma 4 2B (LM Studio ARM64)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "phone": {
        "triage": {
            "model": "Qwen2.5-1.5B (llama.cpp / Termux)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "arduino": {
        "triage": {
            "model": "Qwen2.5-0.5B Q4 (llama.cpp on QRB2210)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "cloud": {
        "triage": {
            "model": "gpt-4o",
            "adapter": "openai_cloud",
            "type": "cloud"
        }
    }
}


# ==========================================================
# CHANGE ONLY THIS LINE
# ==========================================================

ACTIVE_REGISTRY = DEV_REGISTRY

# At the venue simply change to:
# ACTIVE_REGISTRY = QUALCOMM_REGISTRY

# Contract device_ids (from contracts/topics.py + runtime/configs/*.yaml) mapped to
# the registry's friendly keys, so the runtime agent can pass its raw device_id
# (e.g. "pc-01") straight into run_model(). Friendly keys map to themselves too.
DEVICE_ALIASES = {
    "pc-01": "surface", "surface": "surface",
    "phone-01": "phone", "phone": "phone",
    "arduino-01": "arduino", "arduino": "arduino", "unoq": "arduino",
    "cloud-01": "cloud", "cloud": "cloud",
}


def get_model_config(device: str, task: str) -> dict:
    """
    Returns the model configuration for a given device and task.

    Accepts either a registry key ("surface") or a contract device_id
    ("pc-01") — the latter is resolved via DEVICE_ALIASES.
    """

    key = DEVICE_ALIASES.get(device, device)

    if key not in ACTIVE_REGISTRY:
        raise ValueError(f"Unsupported device: {device}")

    if task not in ACTIVE_REGISTRY[key]:
        raise ValueError(
            f"Task '{task}' not supported on device '{device}'"
        )

    return ACTIVE_REGISTRY[key][task]
