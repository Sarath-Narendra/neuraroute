"""Telemetry helpers for NeuraRoute device agents.

This module provides lightweight, dependency-safe telemetry values for PCs,
phones, and Arduino-style devices. It also supports a demo-only critical-battery
override for on-stage failover demonstrations.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None


_SCRIPTED_START_TIMES: dict[str, float] = {}
_CRITICAL_BATTERY_OVERRIDES: dict[str, bool] = {}


def _scripted_drain(device_id: str | None) -> float:
    """Return a deterministic battery level that drains over time.

    Battery starts at 95.0 and decreases by 0.5 points per second since the
    first call for the given device_id, floored at 5.0.
    """
    resolved_device_id = device_id or "default-device"
    if resolved_device_id not in _SCRIPTED_START_TIMES:
        _SCRIPTED_START_TIMES[resolved_device_id] = time.time()

    elapsed_seconds = max(0.0, time.time() - _SCRIPTED_START_TIMES[resolved_device_id])
    return max(5.0, 95.0 - (elapsed_seconds * 0.5))


def simulate_battery_critical(device_id: str) -> None:
    """Force the next telemetry read for device_id to report battery=2.0."""
    _CRITICAL_BATTERY_OVERRIDES[device_id] = True


def clear_override(device_id: str) -> None:
    """Clear the critical battery override for device_id."""
    _CRITICAL_BATTERY_OVERRIDES.pop(device_id, None)


def _apply_critical_override(device_id: str | None, battery: Any) -> Any:
    if device_id and _CRITICAL_BATTERY_OVERRIDES.get(device_id):
        _CRITICAL_BATTERY_OVERRIDES.pop(device_id, None)
        return 2.0
    return battery


def get_telemetry(device_type: str, mode: str, device_id: str | None = None) -> dict[str, Any]:
    """Return telemetry values for the requested device type and mode."""
    device_type = (device_type or "pc").lower()
    mode = (mode or "simulated").lower()

    if device_type == "pc":
        values = _get_pc_telemetry(mode, device_id)
    elif device_type == "phone":
        values = _get_phone_telemetry(mode, device_id)
    elif device_type == "arduino":
        values = _get_arduino_telemetry(mode, device_id)
    else:
        values = {
            "battery": None,
            "cpu_load": 0.0,
            "npu_load": None,
        }

    values["battery"] = _apply_critical_override(device_id, values.get("battery"))
    return values


def _get_pc_telemetry(mode: str, device_id: str | None) -> dict[str, Any]:
    if mode == "real":
        battery = None
        cpu_load = 0.0

        if psutil is not None:
            try:
                cpu_load = float(psutil.cpu_percent(interval=None))
            except Exception:
                cpu_load = 0.0

            try:
                battery_info = psutil.sensors_battery()
                if battery_info is not None:
                    battery = max(0.0, min(100.0, float(battery_info.percent)))
            except Exception:
                battery = None

        return {
            "battery": battery,
            "cpu_load": cpu_load,
            "npu_load": None,
        }

    return {
        "battery": _scripted_drain(device_id),
        "cpu_load": 25.0,
        "npu_load": None,
    }


def _get_phone_telemetry(mode: str, device_id: str | None) -> dict[str, Any]:
    if mode == "real":
        battery = None
        cpu_load = 10.0

        try:
            result = subprocess.run(
                ["termux-battery-status"],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                data = result.stdout.strip()
                if data:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict):
                        percentage = parsed.get("percentage")
                        if isinstance(percentage, (int, float)):
                            battery = max(0.0, min(100.0, float(percentage)))
        except Exception:
            battery = None

        if battery is None:
            battery = _scripted_drain(device_id)

        return {
            "battery": battery,
            "cpu_load": cpu_load,
            "npu_load": None,
        }

    return {
        "battery": _scripted_drain(device_id),
        "cpu_load": 10.0,
        "npu_load": None,
    }


def _get_arduino_telemetry(mode: str, device_id: str | None) -> dict[str, Any]:
    return {
        "battery": _scripted_drain(device_id),
        "cpu_load": 5.0,
        "npu_load": None,
    }

if __name__ == "__main__":
    import json

    print("PC (real):")
    print(json.dumps(get_telemetry("pc", "real"), indent=2))

    print("\nPC (simulated):")
    print(json.dumps(get_telemetry("pc", "simulated", device_id="pc-test"), indent=2))