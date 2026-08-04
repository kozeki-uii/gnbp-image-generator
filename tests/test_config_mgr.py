import copy
import json
import os
import tempfile
import unittest

from config.config_mgr import ConfigManager, DEFAULT_CONFIG


class ConfigManagerTests(unittest.TestCase):
    def test_load_fills_new_default_settings_without_overwriting_user_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            data = {
                "profiles": [],
                "prompts": [],
                "settings": {"show_preview": False},
            }
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)

            settings = ConfigManager(path).get_settings()

            self.assertFalse(settings["show_preview"])
            self.assertEqual(settings["batch_count"], 1)
            self.assertEqual(settings["max_workers"], 1)
            self.assertEqual(settings["history_limit"], 60)
            self.assertTrue(settings["sound_notify"])
            self.assertEqual(settings["theme"], "米黄")

    def test_selecting_profile_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            data = copy.deepcopy(DEFAULT_CONFIG)
            data["profiles"].append(
                {
                    "name": "Second",
                    "api_type": "gemini",
                    "api_url": "https://example.invalid",
                    "api_key": "",
                    "model": "model",
                }
            )
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)

            ConfigManager(path).set_current_profile_idx(1)

            self.assertEqual(ConfigManager(path).data["current_profile_idx"], 1)

    def test_old_profiles_default_to_images_api_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            data = copy.deepcopy(DEFAULT_CONFIG)
            data["profiles"][0].pop("api_mode", None)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)

            profile = ConfigManager(path).get_current_profile()

            self.assertEqual(profile["api_mode"], "images")


if __name__ == "__main__":
    unittest.main()
