import base64
import json
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QByteArray, QBuffer, QEvent, QIODevice, QMimeDatabase, QSettings, QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImage, QKeySequence, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QWidget

from app_info import APP_TITLE


DESKTOP_PORT = 47831
DEFAULT_ZOOM = 1.25
MAX_DESKTOP_IMAGE_BYTES = 64 * 1024 * 1024
DESKTOP_IMAGES_EVENT = "gnbp-desktop-images"
DESKTOP_DRAG_STATE_EVENT = "gnbp-desktop-drag-state"


def get_resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


def _image_file_to_data_url(path):
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > MAX_DESKTOP_IMAGE_BYTES:
            return None
        mime_type = QMimeDatabase().mimeTypeForFile(path, QMimeDatabase.MatchContent).name()
        if not mime_type.startswith("image/"):
            return None
        with open(path, "rb") as handle:
            payload = base64.b64encode(handle.read()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime_type};base64,{payload}"


def mime_data_has_images(mime_data):
    if mime_data.hasImage():
        return True
    return any(
        url.isLocalFile()
        and QMimeDatabase().mimeTypeForFile(url.toLocalFile(), QMimeDatabase.MatchExtension).name().startswith("image/")
        for url in mime_data.urls()
    )


def mime_data_to_image_data_urls(mime_data):
    data_urls = []
    for url in mime_data.urls():
        if not url.isLocalFile():
            continue
        data_url = _image_file_to_data_url(url.toLocalFile())
        if data_url:
            data_urls.append(data_url)

    if data_urls or not mime_data.hasImage():
        return data_urls

    image_data = mime_data.imageData()
    if hasattr(image_data, "toImage"):
        image = image_data.toImage()
    elif isinstance(image_data, QImage):
        image = image_data
    else:
        image = QImage(image_data)
    if image.isNull():
        return []

    encoded = QByteArray()
    buffer = QBuffer(encoded)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not image.save(buffer, "PNG"):
        return []
    payload = base64.b64encode(bytes(encoded)).decode("ascii")
    return [f"data:image/png;base64,{payload}"]


class QuietStaticHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        return

    def end_headers(self):
        if self.path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
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


class DesktopWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._desktop_drag_active = False
        self.installEventFilter(self)
        self.loadFinished.connect(lambda _success: QTimer.singleShot(0, self._enable_desktop_drops))

    def _enable_desktop_drops(self):
        self.setAcceptDrops(True)
        for child in self.findChildren(QWidget):
            child.setAcceptDrops(True)
            child.installEventFilter(self)

    def _owns_event_target(self, watched):
        return watched is self or (isinstance(watched, QWidget) and self.isAncestorOf(watched))

    def eventFilter(self, watched, event):
        if not self._owns_event_target(watched):
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.Type.DragEnter and mime_data_has_images(event.mimeData()):
            self._desktop_drag_active = True
            self._set_drag_active(True)
            event.acceptProposedAction()
            return True
        if event_type == QEvent.Type.DragMove and self._desktop_drag_active:
            event.acceptProposedAction()
            return True
        if event_type == QEvent.Type.DragLeave and self._desktop_drag_active:
            self._desktop_drag_active = False
            self._set_drag_active(False)
            event.accept()
            return True
        if event_type == QEvent.Type.Drop:
            self._desktop_drag_active = False
            self._set_drag_active(False)
            data_urls = mime_data_to_image_data_urls(event.mimeData())
            if data_urls:
                self._dispatch_desktop_event(DESKTOP_IMAGES_EVENT, data_urls)
                event.acceptProposedAction()
                return True

        return super().eventFilter(watched, event)

    def _dispatch_desktop_event(self, event_name, detail):
        script = (
            f"window.dispatchEvent(new CustomEvent({json.dumps(event_name)}, "
            f"{{detail: {json.dumps(detail)}}}));"
        )
        self.page().runJavaScript(script)

    def _set_drag_active(self, active):
        self._dispatch_desktop_event(DESKTOP_DRAG_STATE_EVENT, bool(active))

    def paste_clipboard_images(self):
        data_urls = mime_data_to_image_data_urls(QApplication.clipboard().mimeData())
        if not data_urls:
            return False
        self._dispatch_desktop_event(DESKTOP_IMAGES_EVENT, data_urls)
        return True

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste) and self.paste_clipboard_images():
            event.accept()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if mime_data_has_images(event.mimeData()):
            self._desktop_drag_active = True
            self._set_drag_active(True)
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._desktop_drag_active:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._desktop_drag_active = False
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._desktop_drag_active = False
        self._set_drag_active(False)
        data_urls = mime_data_to_image_data_urls(event.mimeData())
        if data_urls:
            self._dispatch_desktop_event(DESKTOP_IMAGES_EVENT, data_urls)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


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
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.setHttpCacheMaximumSize(128 * 1024 * 1024)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        profile.downloadRequested.connect(self._handle_download)

        desktop_runtime = QWebEngineScript()
        desktop_runtime.setName("GNBP desktop runtime")
        desktop_runtime.setInjectionPoint(QWebEngineScript.DocumentCreation)
        desktop_runtime.setWorldId(QWebEngineScript.MainWorld)
        desktop_runtime.setRunsOnSubFrames(False)
        desktop_runtime.setSourceCode(
            "window.__GNBP_DESKTOP__ = true;"
            "document.documentElement.dataset.gnbpDesktop = 'true';"
        )
        profile.scripts().insert(desktop_runtime)
        self.web_profile = profile

        self.web_view = DesktopWebView(self)
        page = DesktopWebPage(profile, self.web_view)
        page.setBackgroundColor(QColor("#111827"))
        page.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        page.settings().setAttribute(QWebEngineSettings.JavascriptCanPaste, True)
        page.settings().setAttribute(QWebEngineSettings.NavigateOnDropEnabled, False)
        self.web_view.setPage(page)
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
