"""Persistent user preferences for Scoundrel V2."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_SETTINGS = {
    "confirm_forced_barehand": False,
    "allow_equal_weapon_kills": True,
}


class SettingsStore:
    """Small preferences store backed by human-readable JSON."""

    def __init__(self, path: Path):
        self.path = path
        self.values = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            for key in DEFAULT_SETTINGS:
                value = loaded.get(key)
                if isinstance(value, bool):
                    self.values[key] = value
            self.save()  # Also migrates older settings files to new keys.
        except (OSError, json.JSONDecodeError, AttributeError):
            self.save()

    def save(self) -> None:
        try:
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.values, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            pass  # The game remains playable if its folder becomes read-only.

    def toggle(self, key: str) -> bool:
        self.values[key] = not bool(self.values[key])
        self.save()
        return self.values[key]
