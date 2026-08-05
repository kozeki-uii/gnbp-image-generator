import base64
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QColor, QImage

from ui.web_window import mime_data_has_images, mime_data_to_image_data_urls


class DesktopImageTransferTests(unittest.TestCase):
    def test_clipboard_bitmap_becomes_png_data_url(self):
        image = QImage(3, 2, QImage.Format.Format_ARGB32)
        image.fill(QColor("#336699"))
        mime_data = QMimeData()
        mime_data.setImageData(image)

        data_urls = mime_data_to_image_data_urls(mime_data)

        self.assertTrue(mime_data_has_images(mime_data))
        self.assertEqual(len(data_urls), 1)
        prefix, payload = data_urls[0].split(",", 1)
        self.assertEqual(prefix, "data:image/png;base64")
        self.assertTrue(base64.b64decode(payload).startswith(b"\x89PNG"))

    def test_dropped_image_file_keeps_file_mime_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "reference.png")
            image = QImage(2, 2, QImage.Format.Format_ARGB32)
            image.fill(QColor("#cc8844"))
            self.assertTrue(image.save(path, "PNG"))
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(path)])

            data_urls = mime_data_to_image_data_urls(mime_data)

        self.assertTrue(mime_data_has_images(mime_data))
        self.assertEqual(len(data_urls), 1)
        self.assertTrue(data_urls[0].startswith("data:image/png;base64,"))

    def test_non_image_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "notes.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("not an image")
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(path)])

            self.assertFalse(mime_data_has_images(mime_data))
            self.assertEqual(mime_data_to_image_data_urls(mime_data), [])


if __name__ == "__main__":
    unittest.main()
