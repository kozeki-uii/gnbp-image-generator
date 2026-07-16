import copy
import json
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app_info import APP_TITLE
from config.config_mgr import DEFAULT_CONFIG
import ui.main_window as main_window


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_batch_count_is_persisted_when_changed(self):
        original_config_file = main_window.CONFIG_FILE
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "config.json")
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(copy.deepcopy(DEFAULT_CONFIG), handle)

                main_window.CONFIG_FILE = path
                window = main_window.MainWindow()
                self.assertEqual(window.windowTitle(), APP_TITLE)
                window.batch_spin.setValue(7)
                self.app.processEvents()
                window.close()

                with open(path, "r", encoding="utf-8") as handle:
                    settings = json.load(handle)["settings"]

                self.assertEqual(settings["batch_count"], 7)
        finally:
            main_window.CONFIG_FILE = original_config_file


if __name__ == "__main__":
    unittest.main()
