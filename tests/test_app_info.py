import unittest

from app_info import (
    APP_AUTHOR,
    APP_EXECUTABLE_NAME,
    APP_NAME,
    APP_TITLE,
    APP_VERSION,
)


class AppInfoTests(unittest.TestCase):
    def test_display_and_executable_names_come_from_version(self):
        self.assertEqual(
            APP_TITLE,
            f"{APP_NAME} V{APP_VERSION} | Developed by {APP_AUTHOR}",
        )
        self.assertEqual(
            APP_EXECUTABLE_NAME,
            f"GNBP-Image-Generator_V{APP_VERSION}",
        )


if __name__ == "__main__":
    unittest.main()
