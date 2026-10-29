import json
from pathlib import Path
import tempfile
import unittest

from scoundrel.settings import SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_toggle_is_written_and_loaded_by_next_session(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            first = SettingsStore(path)
            self.assertFalse(first.values["confirm_forced_barehand"])
            self.assertTrue(first.values["allow_equal_weapon_kills"])
            self.assertTrue(first.toggle("confirm_forced_barehand"))
            self.assertFalse(first.toggle("allow_equal_weapon_kills"))
            second = SettingsStore(path)
            self.assertTrue(second.values["confirm_forced_barehand"])
            self.assertFalse(second.values["allow_equal_weapon_kills"])
            self.assertTrue(json.loads(path.read_text())["confirm_forced_barehand"])

    def test_invalid_json_recovers_to_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("not json")
            store = SettingsStore(path)
            self.assertFalse(store.values["confirm_forced_barehand"])
            self.assertTrue(store.values["allow_equal_weapon_kills"])
            self.assertFalse(json.loads(path.read_text())["confirm_forced_barehand"])


if __name__ == "__main__":
    unittest.main()
