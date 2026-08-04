import sys
import os

# The desktop shell only renders bundled local content. Disabling Chromium's
# same-origin checks lets that trusted UI call user-configured API endpoints
# directly, matching a native desktop client's networking behavior.
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-web-security --disable-features=BlockInsecurePrivateNetworkRequests",
)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from app_info import APP_NAME, APP_VERSION
from ui.web_window import WebMainWindow


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    icon_path = get_resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = WebMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
