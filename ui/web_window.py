import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QSettings, QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from app_info import APP_TITLE


DESKTOP_PORT = 47831
DEFAULT_ZOOM = 1.25


def get_resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


class LocalFrontendServer:
    def __init__(self, directory, port=DESKTOP_PORT):
        handler = partial(QuietStaticHandler, directory=directory)
        self.server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}/"

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class DesktopWebPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if is_main_frame and url.host() not in {"127.0.0.1", "localhost"}:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)

    def createWindow(self, _window_type):
        page = DesktopWebPage(self.profile(), self)
        page.urlChanged.connect(lambda url: self._open_external(url, page))
        return page

    @staticmethod
    def _open_external(url, page):
        if url.isValid():
            QDesktopServices.openUrl(url)
        page.deleteLater()


class WebMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1080, 700)
        self.resize(1440, 900)

        frontend_dir = get_resource_path("web_dist")
        index_path = os.path.join(frontend_dir, "index.html")
        if not os.path.isfile(index_path):
            raise FileNotFoundError(f"前端文件不存在: {index_path}")

        try:
            self.frontend_server = LocalFrontendServer(frontend_dir)
        except OSError as error:
            raise RuntimeError(f"本地界面端口 {DESKTOP_PORT} 无法使用: {error}") from error
        self.frontend_server.start()

        app_data = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        profile = QWebEngineProfile("GNBPDesktop", self)
        profile.setPersistentStoragePath(os.path.join(app_data, "web-storage"))
        profile.setCachePath(os.path.join(app_data, "web-cache"))
        profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        profile.downloadRequested.connect(self._handle_download)
        self.web_profile = profile

        self.web_view = QWebEngineView(self)
        self.web_view.setPage(DesktopWebPage(profile, self.web_view))
        self.desktop_settings = QSettings("GNBP", "ImageGenerator")
        saved_zoom = self.desktop_settings.value("web_zoom", DEFAULT_ZOOM, type=float)
        self.web_view.setZoomFactor(max(0.75, min(1.50, saved_zoom)))
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.setCentralWidget(self.web_view)
        QShortcut(QKeySequence("Ctrl++"), self, lambda: self._change_zoom(0.05))
        QShortcut(QKeySequence("Ctrl+="), self, lambda: self._change_zoom(0.05))
        QShortcut(QKeySequence("Ctrl+-"), self, lambda: self._change_zoom(-0.05))
        QShortcut(QKeySequence("Ctrl+0"), self, self._reset_zoom)
        self.web_view.setUrl(QUrl(self.frontend_server.url))

    def _change_zoom(self, delta):
        zoom = max(0.75, min(1.50, self.web_view.zoomFactor() + delta))
        self.web_view.setZoomFactor(zoom)
        self.desktop_settings.setValue("web_zoom", zoom)

    def _reset_zoom(self):
        self.web_view.setZoomFactor(DEFAULT_ZOOM)
        self.desktop_settings.setValue("web_zoom", DEFAULT_ZOOM)

    def _on_load_finished(self, success):
        if not success:
            QMessageBox.critical(self, "界面加载失败", "本地前端没有正常加载，请重新启动程序。")

    def _handle_download(self, download):
        default_name = download.downloadFileName() or "download"
        target, _selected_filter = QFileDialog.getSaveFileName(self, "保存文件", default_name)
        if not target:
            download.cancel()
            return
        download.setDownloadDirectory(os.path.dirname(target))
        download.setDownloadFileName(os.path.basename(target))
        download.accept()

    def closeEvent(self, event):
        self.frontend_server.stop()
        super().closeEvent(event)
