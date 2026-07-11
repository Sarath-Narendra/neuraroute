"""Scheduler policy: cost-function weights, hot-reloaded from policy.yaml.

The active profile is flipped live via POST /policy — that's the speed-first <-> battery-saver
demo moment. reload() re-reads the file so an edit to policy.yaml takes effect without a restart.
"""
import os
import threading

import yaml

_POLICY_PATH = os.path.join(os.path.dirname(__file__), "policy.yaml")


class Policy:
    def __init__(self, path: str = _POLICY_PATH):
        self.path = path
        self._lock = threading.Lock()
        self._mtime = 0.0
        self._data = {}
        self.reload(force=True)

    def reload(self, force: bool = False):
        """Re-read policy.yaml if it changed on disk (hot-reload)."""
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            return
        if not force and mtime == self._mtime:
            return
        with open(self.path) as f:
            data = yaml.safe_load(f) or {}
        with self._lock:
            self._data = data
            self._mtime = mtime

    @property
    def active_profile(self) -> str:
        with self._lock:
            return self._data.get("active_profile", "speed_first")

    def set_profile(self, profile: str) -> bool:
        """Flip the active profile in memory (the live demo toggle).

        We deliberately do NOT rewrite policy.yaml — that would strip its comments and reset
        on restart. weights() calls reload(), which only re-reads on an mtime change, so this
        in-memory value survives until someone edits the file on disk (manual hot-reload wins).
        """
        self.reload()
        with self._lock:
            if profile not in self._data.get("profiles", {}):
                return False
            self._data["active_profile"] = profile
        return True

    def weights(self) -> dict:
        """Weights for the active profile, hot-reloading first. Falls back to sane defaults."""
        self.reload()
        with self._lock:
            profiles = self._data.get("profiles", {})
            prof = profiles.get(self._data.get("active_profile", ""), {})
        return {
            "wL": float(prof.get("wL", 0.6)),
            "wE": float(prof.get("wE", 0.1)),
            "wC": float(prof.get("wC", 0.2)),
            "wP": float(prof.get("wP", 0.3)),
        }
