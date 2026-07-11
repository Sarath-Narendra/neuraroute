"""Simple YAML config loader and validator for NeuraRoute devices.

Run it directly to sanity-check the bundled example configs:
    python runtime/config_loader.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ALLOWED_DEVICE_TYPES = {"pc", "phone", "arduino"}
ALLOWED_TELEMETRY_MODES = {"real", "simulated"}


def load_config(path: str) -> dict[str, Any]:
    """Load and validate a device YAML config file."""
    config_path = Path(path).expanduser()
    if not config_path.exists():
        raise ValueError(f"{path} does not exist")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")

    required_fields = [
        "device_id",
        "device_type",
        "accelerators",
        "supported_ops",
        "telemetry_mode",
    ]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"{path} is missing required field '{field}'")

    device_id = data.get("device_id")
    device_type = data.get("device_type")
    accelerators = data.get("accelerators")
    supported_ops = data.get("supported_ops")
    telemetry_mode = data.get("telemetry_mode")

    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError(f"{path} has invalid field 'device_id'")
    if not isinstance(device_type, str) or device_type not in ALLOWED_DEVICE_TYPES:
        raise ValueError(
            f"{path} has invalid field 'device_type': expected one of {sorted(ALLOWED_DEVICE_TYPES)}"
        )
    if not isinstance(accelerators, list) or not accelerators or not all(isinstance(item, str) and item.strip() for item in accelerators):
        raise ValueError(f"{path} has invalid field 'accelerators'")
    if not isinstance(supported_ops, list) or not supported_ops or not all(isinstance(item, str) and item.strip() for item in supported_ops):
        raise ValueError(f"{path} has invalid field 'supported_ops'")
    if not isinstance(telemetry_mode, str) or telemetry_mode not in ALLOWED_TELEMETRY_MODES:
        raise ValueError(
            f"{path} has invalid field 'telemetry_mode': expected one of {sorted(ALLOWED_TELEMETRY_MODES)}"
        )

    return data


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    config_files = [base_dir / "configs" / name for name in ["pc.yaml", "phone.yaml", "arduino.yaml"]]
    for config_file in config_files:
        try:
            parsed = load_config(str(config_file))
        except ValueError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        print(f"{config_file.name}:")
        print(yaml.safe_dump(parsed, sort_keys=False))
