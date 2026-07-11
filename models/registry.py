"""
models/registry.py

Central Model Registry

DEV_REGISTRY
    -> Used on your own laptop

QUALCOMM_REGISTRY
    -> Used on the Snapdragon hackathon laptop

Simply change:

ACTIVE_REGISTRY = DEV_REGISTRY

to

ACTIVE_REGISTRY = QUALCOMM_REGISTRY

during the hackathon.
"""

# ==========================================================
# LOCAL DEVELOPMENT (Your Laptop)
# ==========================================================

DEV_REGISTRY = {

    "surface": {

        "extract_text": {
            "model": "PyMuPDF",
            "adapter": "pymupdf",
            "type": "local"
        },

        "summarize": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        },

        "flag_risk": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        },

        "patient_explainer": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "phone": {

        "extract_text": {
            "model": "PyMuPDF",
            "adapter": "pymupdf",
            "type": "local"
        },

        "summarize": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        },

        "flag_risk": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        },

        "patient_explainer": {
            "model": "Phi-3 (LM Studio)",
            "adapter": "llm_client",
            "type": "local"
        }
    },

    "cloud": {

        "population_stats": {
            "model": "Qualcomm AI Cloud",
            "adapter": "qualcomm_cloud",
            "type": "cloud"
        }
    }
}


# ==========================================================
# QUALCOMM HACKATHON LAPTOP
# ==========================================================

QUALCOMM_REGISTRY = {

    "surface": {

        "extract_text": {
            "model": "PyMuPDF",
            "adapter": "pymupdf",
            "type": "local"
        },

        "summarize": {
            "model": "Gemma 4 2B",
            "adapter": "gemma",
            "type": "local"
        },

        "flag_risk": {
            "model": "Qwen 3 1.7B",
            "adapter": "qwen",
            "type": "local"
        },

        "patient_explainer": {
            "model": "Gemma 4 2B",
            "adapter": "gemma",
            "type": "local"
        }
    },

    "phone": {

        "extract_text": {
            "model": "PyMuPDF",
            "adapter": "pymupdf",
            "type": "local"
        },

        "summarize": {
            "model": "SmolVLM 500M",
            "adapter": "smolvlm",
            "type": "local"
        },

        "flag_risk": {
            "model": "SmolVLM 500M",
            "adapter": "smolvlm",
            "type": "local"
        },

        "patient_explainer": {
            "model": "SmolVLM 500M",
            "adapter": "smolvlm",
            "type": "local"
        }
    },

    "cloud": {

        "population_stats": {
            "model": "Qualcomm AI Cloud",
            "adapter": "qualcomm_cloud",
            "type": "cloud"
        }
    }
}


# ==========================================================
# CHANGE ONLY THIS LINE
# ==========================================================

ACTIVE_REGISTRY = DEV_REGISTRY

# Tomorrow at the hackathon simply change to:
# ACTIVE_REGISTRY = QUALCOMM_REGISTRY


def get_model_config(device: str, task: str) -> dict:
    """
    Returns the model configuration for a given device and task.
    """

    if device not in ACTIVE_REGISTRY:
        raise ValueError(f"Unsupported device: {device}")

    if task not in ACTIVE_REGISTRY[device]:
        raise ValueError(
            f"Task '{task}' not supported on device '{device}'"
        )

    return ACTIVE_REGISTRY[device][task]