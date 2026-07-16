import os
import tempfile
from string import Template
from PIL import Image, ImageDraw

THEMES = {
    "纯白": {
        "bg": "#F8F9FA", "card": "#FFFFFF", "card_alt": "#F0F1F2",
        "border": "#DEE2E6", "border_light": "#E9ECEF",
        "text": "#212529", "text_secondary": "#6C757D",
        "primary": "#0D6EFD", "primary_hover": "#0B5ED7", "primary_pressed": "#0A58CA",
        "success": "#198754", "success_hover": "#157347",
        "danger": "#DC3545", "danger_hover": "#BB2D3B",
        "selection_bg": "#E7F1FF", "scrollbar": "#ADB5BD", "scrollbar_hover": "#6C757D",
        "log_text": "#198754", "log_bg": "#F8F9FA", "checkbox_bg": "#0D6EFD",
        "title_color": "#0D6EFD",
    },
    "米黄": {
        "bg": "#F5F0E8", "card": "#FFFFFF", "card_alt": "#EDE8DF",
        "border": "#D4C9B8", "border_light": "#E8E2D8",
        "text": "#333333", "text_secondary": "#888888",
        "primary": "#5B86B8", "primary_hover": "#4A739F", "primary_pressed": "#3D6088",
        "success": "#4CAF50", "success_hover": "#43A047",
        "danger": "#E57373", "danger_hover": "#EF5350",
        "selection_bg": "#E8F0FA", "scrollbar": "#C4B9A8", "scrollbar_hover": "#A89888",
        "log_text": "#2E7D32", "log_bg": "#FAF8F4", "checkbox_bg": "#5B86B8",
        "title_color": "#5B86B8",
    },
    "纯黑": {
        "bg": "#1A1A1A", "card": "#2A2A2A", "card_alt": "#303030",
        "border": "#404040", "border_light": "#383838",
        "text": "#E0E0E0", "text_secondary": "#999999",
        "primary": "#5B9BD5", "primary_hover": "#4A88C2", "primary_pressed": "#3A78B2",
        "success": "#66BB6A", "success_hover": "#57A05A",
        "danger": "#EF5350", "danger_hover": "#F44336",
        "selection_bg": "#2C3E50", "scrollbar": "#555555", "scrollbar_hover": "#777777",
        "log_text": "#66BB6A", "log_bg": "#1E1E1E", "checkbox_bg": "#5B9BD5",
        "title_color": "#5B9BD5",
    },
    "深蓝": {
        "bg": "#1B2838", "card": "#1E2D42", "card_alt": "#233550",
        "border": "#2A4060", "border_light": "#253A55",
        "text": "#C7D5E0", "text_secondary": "#8F98A0",
        "primary": "#66C0F4", "primary_hover": "#55A8D8", "primary_pressed": "#4490BC",
        "success": "#5BA32B", "success_hover": "#4D8B24",
        "danger": "#CD5444", "danger_hover": "#D95D4E",
        "selection_bg": "#2A475E", "scrollbar": "#3A5672", "scrollbar_hover": "#4A6882",
        "log_text": "#5BA32B", "log_bg": "#171D28", "checkbox_bg": "#66C0F4",
        "title_color": "#66C0F4",
    },
}

THEME_NAMES = list(THEMES.keys())

# --- Arrow image generation (Qt QSS needs real images for arrows) ---

_arrow_dir = None
_arrow_cache = {}


def _get_arrow_dir():
    global _arrow_dir
    if _arrow_dir is None:
        _arrow_dir = os.path.join(tempfile.gettempdir(), "gnbp_arrows")
        os.makedirs(_arrow_dir, exist_ok=True)
    return _arrow_dir


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _generate_arrows(color_hex, theme_name):
    key = f"{theme_name}_{color_hex}"
    if key in _arrow_cache:
        return _arrow_cache[key]

    r, g, b = _hex_to_rgb(color_hex)
    d = _get_arrow_dir()

    down = Image.new("RGBA", (10, 6), (0, 0, 0, 0))
    ImageDraw.Draw(down).polygon([(1, 0), (9, 0), (5, 5)], fill=(r, g, b, 255))
    down_path = os.path.join(d, f"down_{theme_name}.png")
    down.save(down_path)

    up = Image.new("RGBA", (10, 6), (0, 0, 0, 0))
    ImageDraw.Draw(up).polygon([(1, 5), (9, 5), (5, 0)], fill=(r, g, b, 255))
    up_path = os.path.join(d, f"up_{theme_name}.png")
    up.save(up_path)

    result = {
        "arrow_down": down_path.replace("\\", "/"),
        "arrow_up": up_path.replace("\\", "/"),
    }
    _arrow_cache[key] = result
    return result


# --- QSS Template ---

_QSS = Template("""
* {
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 10pt;
}
QMainWindow, QWidget {
    background: $bg;
    color: $text;
}
QGroupBox {
    border: 1px solid $border;
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px 10px 6px 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: $title_color;
}
QPushButton {
    background: $primary;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 6px 14px;
    min-height: 22px;
    outline: none;
}
QPushButton:hover { background: $primary_hover; }
QPushButton:pressed { background: $primary_pressed; }
QPushButton:focus { outline: none; border: none; }
QPushButton[cssClass="success"] {
    background: $success;
    font-size: 11pt;
    font-weight: bold;
    padding: 10px;
    border-radius: 6px;
}
QPushButton[cssClass="success"]:hover { background: $success_hover; }
QPushButton[cssClass="danger"] { background: $danger; }
QPushButton[cssClass="danger"]:hover { background: $danger_hover; }
QPushButton[cssClass="link"] {
    background: transparent;
    color: $primary;
    padding: 4px 8px;
}
QPushButton[cssClass="link"]:hover { color: $primary_hover; }
QPushButton[cssClass="link"]:focus { outline: none; border: none; }
QPushButton[cssClass="table-action"] {
    background: $primary;
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 9pt;
    min-height: 20px;
}
QPushButton[cssClass="table-action"]:hover { background: $primary_hover; }
QPushButton[cssClass="table-action"]:focus { outline: none; border: none; }
QPushButton[cssClass="table-action-danger"] {
    background: $danger;
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 9pt;
    min-height: 20px;
}
QPushButton[cssClass="table-action-danger"]:hover { background: $danger_hover; }
QPushButton[cssClass="table-action-danger"]:focus { outline: none; border: none; }
QLineEdit, QComboBox, QSpinBox {
    background: $card;
    color: $text;
    border: 1px solid $border;
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 22px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: $primary; }
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: url($arrow_down);
    width: 10px;
    height: 6px;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    border: none;
    background: transparent;
    width: 16px;
    padding-right: 4px;
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border: none;
    background: transparent;
    width: 16px;
    padding-right: 4px;
}
QSpinBox::up-arrow {
    image: url($arrow_up);
    width: 8px;
    height: 5px;
}
QSpinBox::down-arrow {
    image: url($arrow_down);
    width: 8px;
    height: 5px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: $selection_bg;
    border-radius: 3px;
}
QComboBox QAbstractItemView {
    background: $card;
    color: $text;
    selection-background-color: $primary;
    selection-color: #ffffff;
    border: 1px solid $border;
}
QTextEdit {
    background: $card;
    color: $text;
    border: 1px solid $border;
    border-radius: 5px;
    selection-background-color: $primary;
    selection-color: #ffffff;
    font-size: 11pt;
}
QTabWidget::pane {
    border: 1px solid $border;
    border-radius: 5px;
    top: -1px;
    background: $card;
}
QTabBar::tab {
    background: $card_alt;
    color: $text_secondary;
    padding: 6px 16px;
    border: 1px solid $border;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: $card;
    color: $text;
    border-bottom: 2px solid $primary;
}
QTabBar::tab:hover:!selected {
    background: $bg;
    color: $text;
}
QTableWidget {
    background: $card;
    color: $text;
    gridline-color: $border_light;
    border: none;
    selection-background-color: $selection_bg;
    selection-color: $text;
}
QTableWidget::item { padding: 4px; }
QHeaderView::section {
    background: $card_alt;
    color: $text_secondary;
    border: none;
    border-bottom: 1px solid $border;
    border-right: 1px solid $border_light;
    padding: 6px 8px;
    font-weight: bold;
}
QScrollBar:vertical {
    background: $card_alt;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: $scrollbar;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: $scrollbar_hover; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: $card_alt;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: $scrollbar;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: $scrollbar_hover; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: $border; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }
QTextEdit[readOnly="true"] {
    font-family: "Consolas", monospace;
    font-size: 9pt;
    color: $log_text;
    background: $log_bg;
}
QLabel { color: $text; }
QLabel[cssClass="meta"] { color: $primary; font-size: 9pt; }
QLabel[cssClass="preview-placeholder"] {
    background: $card_alt;
    border-radius: 6px;
    color: $text_secondary;
    font-size: 14pt;
}
QLabel[cssClass="ref-count"] { color: $text_secondary; font-size: 9pt; }
QCheckBox { spacing: 8px; color: $text; }
QCheckBox::indicator {
    width: 36px;
    height: 18px;
    border-radius: 9px;
    background: $border;
}
QCheckBox::indicator:checked {
    background: $success;
}
QToolTip {
    background: $card;
    color: $text;
    border: 1px solid $border;
    padding: 4px 8px;
    border-radius: 4px;
}
QScrollArea {
    background: $card;
    border: 1px solid $border;
    border-radius: 5px;
}
QGraphicsView {
    background: $card_alt;
    border-radius: 6px;
    border: none;
}
QMenu {
    background: $card;
    color: $text;
    border: 1px solid $border;
    border-radius: 4px;
    padding: 4px 0;
}
QMenu::item { padding: 6px 24px; }
QMenu::item:selected { background: $selection_bg; color: $text; }
QMenu::separator { height: 1px; background: $border_light; margin: 4px 8px; }
QMessageBox, QInputDialog { background: $bg; }
""")


def get_qss(theme_name):
    palette = THEMES.get(theme_name, THEMES["米黄"])
    arrows = _generate_arrows(palette["text_secondary"], theme_name)
    data = {**palette, **arrows}
    return _QSS.substitute(data)
