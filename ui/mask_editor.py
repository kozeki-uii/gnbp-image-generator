import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class MaskCanvas(QWidget):
    def __init__(self, image_path, mask_path=None, parent=None):
        super().__init__(parent)
        self.source = QImage(image_path).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        self.mask = self._load_mask(mask_path)
        self.brush_size = 64
        self.tool = "brush"
        self._drawing = False
        self._last_point = None
        self._undo = []
        self._redo = []
        self.setMinimumSize(640, 480)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    def set_brush_size(self, value):
        self.brush_size = max(1, int(value))

    def _load_mask(self, mask_path):
        if mask_path and os.path.isfile(mask_path):
            mask = QImage(mask_path).convertToFormat(QImage.Format_ARGB32_Premultiplied)
            if mask.size() == self.source.size():
                return mask
        mask = QImage(self.source.size(), QImage.Format_ARGB32_Premultiplied)
        mask.fill(Qt.white)
        return mask

    def image_rect(self):
        if self.source.isNull():
            return QRectF()
        source_size = self.source.size()
        scale = min(self.width() / source_size.width(), self.height() / source_size.height())
        width = source_size.width() * scale
        height = source_size.height() * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def _image_point(self, point):
        rect = self.image_rect()
        if not rect.contains(point):
            return None
        x = (point.x() - rect.left()) / rect.width() * self.source.width()
        y = (point.y() - rect.top()) / rect.height() * self.source.height()
        return QPointF(x, y)

    def _push_undo(self):
        self._undo.append(self.mask.copy())
        if len(self._undo) > 40:
            self._undo.pop(0)
        self._redo.clear()

    def _draw_at(self, point):
        painter = QPainter(self.mask)
        if self.tool == "brush":
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            painter.setBrush(Qt.white)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setBrush(Qt.white)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(point, self.brush_size / 2, self.brush_size / 2)
        painter.end()
        self.update()

    def _draw_line(self, start, end):
        painter = QPainter(self.mask)
        if self.tool == "brush":
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setPen(QPen(Qt.white, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(start, end)
        painter.end()
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        point = self._image_point(event.position())
        if point is None:
            return
        self._push_undo()
        self._drawing = True
        self._last_point = point
        self._draw_at(point)

    def mouseMoveEvent(self, event):
        if not self._drawing or self._last_point is None:
            return
        point = self._image_point(event.position())
        if point is None:
            return
        self._draw_line(self._last_point, point)
        self._last_point = point

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drawing = False
            self._last_point = None

    def undo(self):
        if not self._undo:
            return
        self._redo.append(self.mask.copy())
        self.mask = self._undo.pop()
        self.update()

    def redo(self):
        if not self._redo:
            return
        self._undo.append(self.mask.copy())
        self.mask = self._redo.pop()
        self.update()

    def clear(self):
        self._push_undo()
        self.mask.fill(Qt.white)
        self.update()

    def get_mask(self):
        return self.mask.copy()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202124"))
        rect = self.image_rect()
        if rect.isNull():
            painter.end()
            return

        painter.drawImage(rect, self.source)

        overlay = QImage(self.mask.size(), QImage.Format_ARGB32_Premultiplied)
        overlay.fill(QColor(45, 125, 240, 120))
        overlay_painter = QPainter(overlay)
        overlay_painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        overlay_painter.drawImage(0, 0, self.mask)
        overlay_painter.end()
        painter.drawImage(rect, overlay)

        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawRect(rect)
        painter.end()


class MaskEditorDialog(QDialog):
    def __init__(self, image_path, mask_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("遮罩编辑器")
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("画笔大小:"))
        self.brush_spin = QSpinBox()
        self.brush_spin.setRange(1, 1024)
        self.brush_spin.setValue(64)
        toolbar.addWidget(self.brush_spin)

        self.brush_btn = QPushButton("涂抹区域")
        self.brush_btn.setCheckable(True)
        self.brush_btn.setChecked(True)
        self.brush_btn.clicked.connect(lambda: self._set_tool("brush"))
        toolbar.addWidget(self.brush_btn)

        self.eraser_btn = QPushButton("恢复区域")
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.clicked.connect(lambda: self._set_tool("eraser"))
        toolbar.addWidget(self.eraser_btn)

        undo_btn = QPushButton("撤销")
        undo_btn.clicked.connect(self.canvas_undo)
        toolbar.addWidget(undo_btn)
        redo_btn = QPushButton("重做")
        redo_btn.clicked.connect(self.canvas_redo)
        toolbar.addWidget(redo_btn)
        clear_btn = QPushButton("清空遮罩")
        clear_btn.clicked.connect(self.canvas_clear)
        toolbar.addWidget(clear_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.canvas = MaskCanvas(image_path, mask_path, self)
        self.brush_spin.valueChanged.connect(self.canvas.set_brush_size)
        layout.addWidget(self.canvas, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_tool(self, tool):
        self.canvas.tool = tool
        self.brush_btn.setChecked(tool == "brush")
        self.eraser_btn.setChecked(tool == "eraser")

    def canvas_undo(self):
        self.canvas.undo()

    def canvas_redo(self):
        self.canvas.redo()

    def canvas_clear(self):
        self.canvas.clear()

    def get_mask(self):
        return self.canvas.get_mask()
