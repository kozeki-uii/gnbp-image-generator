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
        "bg": "#F6F7FB", "card": "#FFFFFF", "card_alt": "#EFF2F7",
        "border": "#E0E5EE", "border_light": "#EDF0F5",
        "text": "#1F2937", "text_secondary": "#667085",
        "primary": "#356DFF", "primary_hover": "#2858D7", "primary_pressed": "#1F45B0",
        "success": "#16A36A", "success_hover": "#118256",
        "danger": "#D1495B", "danger_hover": "#B73749",
        "selection_bg": "#E9F0FF", "scrollbar": "#C7CEDB", "scrollbar_hover": "#9DA8BB",
        "log_text": "#157A54", "log_bg": "#F8FAFD", "checkbox_bg": "#356DFF",
        "title_color": "#1F2937",
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
    "Playground Dark": {
        "bg": "#09090B", "card": "#111113", "card_alt": "#18181B",
        "border": "#27272A", "border_light": "#1F1F23",
        "text": "#F4F4F5", "text_secondary": "#A1A1AA",
        "primary": "#3B82F6", "primary_hover": "#2563EB", "primary_pressed": "#1D4ED8",
        "success": "#22C55E", "success_hover": "#16A34A",
        "danger": "#F87171", "danger_hover": "#EF4444",
        "selection_bg": "#1E293B", "scrollbar": "#3F3F46", "scrollbar_hover": "#52525B",
        "log_text": "#86EFAC", "log_bg": "#0F1012", "checkbox_bg": "#3B82F6",
        "title_color": "#F4F4F5",
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


_QSS_MODERN = Template("""
* {
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 10pt;
}
QMainWindow, QWidget { background: $bg; color: $text; }
QFrame#AppHeader { background: $card; border-bottom: 1px solid $border; }
QFrame#MainWorkspace, QWidget#AppSurface { background: $bg; }
QFrame#SidePanel { background: $card; border-left: 1px solid $border; }
QSplitter::handle { background: $border; }
QSplitter::handle:horizontal { width: 1px; }

QLabel#BrandTitle { color: $text; font-size: 11pt; font-weight: 700; }
QLabel#BrandSubtitle { color: $text_secondary; font-size: 7pt; letter-spacing: 1px; }
QPushButton#HeaderToolButton {
    background: transparent; color: $text_secondary; border: none;
    border-radius: 8px; padding: 7px 9px; min-height: 24px; font-size: 13pt;
}
QPushButton#HeaderToolButton:hover { background: $card_alt; color: $text; }
QPushButton#HeaderToolButton:pressed { background: $border; }
QFrame#HeaderModeSwitch {
    background: $card_alt; border: 1px solid $border; border-radius: 11px;
}
QFrame#HeaderModeSwitch QPushButton#HeaderNavButton {
    background: transparent; color: $text_secondary; border: none;
    border-radius: 8px; padding: 6px 13px; min-height: 24px; font-weight: 600;
}
QFrame#HeaderModeSwitch QPushButton#HeaderNavButton:hover { color: $text; background: $border_light; }
QFrame#HeaderModeSwitch QPushButton#HeaderNavButton:checked {
    background: $border; color: $text; border: none;
}
QComboBox#ProfileChip {
    background: $card_alt; color: $text; border: 1px solid $border;
    border-radius: 9px; padding: 5px 10px; min-height: 24px;
}
QComboBox#ProfileChip:hover { border-color: $primary; }

QFrame#SearchBarSurface { background: transparent; }
QPushButton#FavoriteFilterButton, QPushButton#FilterButton {
    background: $card_alt; color: $text_secondary; border: 1px solid $border;
    border-radius: 10px; padding: 7px 12px; min-height: 25px;
}
QPushButton#FavoriteFilterButton:hover, QPushButton#FilterButton:hover,
QPushButton#FavoriteFilterButton:checked {
    background: $border; color: $text; border-color: $primary;
}
QLineEdit#SearchInput {
    background: $card_alt; color: $text; border: 1px solid $border;
    border-radius: 11px; padding: 7px 13px; min-height: 25px;
    selection-background-color: $primary; selection-color: #ffffff;
}
QLineEdit#SearchInput:focus { border-color: $primary; }

QFrame#InputBar {
    background: $card; border: 1px solid $border; border-radius: 18px;
}
QTextEdit#PromptInput {
    background: $card_alt; color: $text; border: 1px solid $border;
    border-radius: 12px; padding: 9px 12px; font-size: 10pt;
    selection-background-color: $primary; selection-color: #ffffff;
}
QTextEdit#PromptInput:focus { border-color: $primary; }
QFrame#ParameterChip {
    background: transparent; border: none; border-radius: 8px;
}
QLabel#ParameterLabel { color: $text_secondary; font-size: 8pt; }
QComboBox#ParameterValue, QSpinBox#ParameterValue {
    background: $card_alt; color: $text; border: 1px solid transparent;
    border-radius: 9px; padding: 3px 8px; min-height: 23px;
}
QComboBox#ParameterValue:hover, QSpinBox#ParameterValue:hover { border-color: $border; }
QComboBox#ParameterValue:focus, QSpinBox#ParameterValue:focus { border-color: $primary; }
QComboBox#ParameterValue::drop-down { border: none; width: 18px; }
QPushButton#ComposerIconButton {
    background: $card_alt; color: $text_secondary; border: 1px solid transparent;
    border-radius: 10px; padding: 7px 10px; min-height: 25px; font-size: 12pt;
}
QPushButton#ComposerIconButton:hover { background: $border; color: $text; border-color: $border; }
QPushButton#ComposerClearButton {
    background: transparent; color: $text_secondary; border: none;
    border-radius: 8px; padding: 6px 9px; min-height: 24px;
}
QPushButton#ComposerClearButton:hover { background: $border; color: $danger; }
QPushButton#GenerateButton {
    background: $text; color: $bg; border: none; border-radius: 10px;
    min-width: 36px; min-height: 36px; padding: 4px 10px; font-size: 15pt; font-weight: 700;
}
QPushButton#GenerateButton:hover { background: #FFFFFF; }
QPushButton#GenerateButton:pressed { background: $primary; color: #FFFFFF; }

QFrame#GalleryCard {
    background: transparent; border: 1px solid transparent; border-radius: 12px;
}
QFrame#GalleryCard:hover { background: $card; border-color: $border; }
QLabel#GalleryThumb { background: $card_alt; border-radius: 10px; }
QLabel#GalleryCardName { color: $text_secondary; padding: 3px 3px 0; font-size: 8pt; }
QLabel#GalleryEmptyState { color: $text_secondary; background: transparent; font-size: 10pt; }

QScrollArea#GalleryScroll { background: transparent; border: none; }
QWidget#GallerySurface { background: transparent; }
QScrollArea#AttachmentScroll { background: transparent; border: none; }
QWidget#AttachmentSurface { background: transparent; }
QLabel#ReferenceThumb { background: $card_alt; border: 1px solid $border; border-radius: 8px; }
QLabel#ReferenceThumb[hasMask="true"] { border: 2px solid $primary; }

QLabel#BrandMark {
    background: $primary; color: #ffffff; border-radius: 8px;
    font-size: 17pt; font-weight: 700;
}
QLabel#BrandTitle { color: $text; font-size: 11pt; font-weight: 700; }
QLabel#BrandSubtitle { color: $text_secondary; font-size: 7pt; letter-spacing: 1px; }
QLabel#HeaderStatus, QLabel#GalleryMeta, QLabel#CharCount, QLabel#AttachmentCount {
    color: $text_secondary; font-size: 9pt;
}
QLabel#PageTitle { color: $text; font-size: 16pt; font-weight: 700; }
QLabel#GalleryCount {
    background: $card_alt; color: $text_secondary; border-radius: 10px;
    padding: 3px 8px; font-size: 9pt;
}
QLabel#SidePanelTitle { color: $text; font-size: 13pt; font-weight: 700; }
QLabel#ComposerLabel { color: $text; font-weight: 600; }
QLabel#SectionHint, QLabel#MaskStatus { color: $text_secondary; font-size: 9pt; }

QPushButton {
    background: $card_alt; color: $text; border: 1px solid $border;
    border-radius: 7px; padding: 6px 12px; min-height: 24px;
}
QPushButton:hover { background: $selection_bg; border-color: $primary; }
QPushButton:pressed { background: $border; }
QPushButton:disabled { color: $text_secondary; background: $border_light; }
QPushButton#HeaderNavButton {
    background: transparent; color: $text_secondary; border: 1px solid transparent;
    padding: 7px 13px; min-height: 26px; font-weight: 600;
}
QPushButton#HeaderNavButton:hover { background: $card_alt; color: $text; }
QPushButton#HeaderNavButton:checked {
    background: $selection_bg; color: $primary; border-color: transparent;
}
QPushButton#IconButton {
    background: transparent; color: $text_secondary; border: none;
    font-size: 16pt; padding: 0;
}
QPushButton#IconButton:hover { background: $card_alt; color: $text; }
QPushButton#GhostButton, QPushButton#InlineButton {
    background: transparent; color: $text_secondary; border-color: transparent;
}
QPushButton#GhostButton:hover, QPushButton#InlineButton:hover {
    background: $selection_bg; color: $primary; border-color: transparent;
}
QPushButton#DangerLinkButton, QPushButton#DangerButton {
    background: transparent; color: $danger; border-color: transparent;
}
QPushButton#DangerLinkButton:hover, QPushButton#DangerButton:hover {
    background: #FCEBED; color: $danger_hover;
}
QPushButton#PrimarySmallButton {
    background: $primary; color: #ffffff; border-color: $primary; font-weight: 600;
}
QPushButton#PrimarySmallButton:hover { background: $primary_hover; }
QPushButton#GenerateButton {
    background: $primary; color: #ffffff; border: none; border-radius: 8px;
    font-size: 12pt; font-weight: 700; padding: 8px 18px;
}
QPushButton#GenerateButton:hover { background: $primary_hover; }
QPushButton#GenerateButton:pressed { background: $primary_pressed; }

QFrame#PromptComposer {
    background: $card; border: 1px solid $border; border-radius: 10px;
}
QTextEdit#PromptInput {
    background: $card; color: $text; border: 1px solid $border; border-radius: 8px;
    padding: 9px 11px; font-size: 11pt;
    selection-background-color: $primary; selection-color: #ffffff;
}
QTextEdit#PromptInput:focus { border-color: $primary; }
QComboBox#PresetCombo, QComboBox#ProfileChip {
    background: $card_alt; border-color: $border; border-radius: 8px;
}
QComboBox#ProfileChip { padding-left: 10px; font-weight: 600; }

QScrollArea#GalleryScroll { background: transparent; border: none; }
QWidget#GallerySurface { background: transparent; }
QFrame#GalleryCard {
    background: $card; border: 1px solid $border; border-radius: 8px;
}
QFrame#GalleryCard:hover { border-color: $primary; background: $card; }
QLabel#GalleryThumb { background: $card_alt; border-radius: 6px; }
QLabel#GalleryCardName {
    color: $text_secondary; padding-left: 2px; font-size: 9pt;
}
QLabel#GalleryEmptyState {
    color: $text_secondary; background: transparent; font-size: 12pt;
}

QScrollArea#AttachmentScroll {
    background: $card_alt; border: 1px solid $border_light; border-radius: 8px;
}
QWidget#AttachmentSurface { background: $card_alt; }
QLabel#AttachmentPlaceholder { color: $text_secondary; padding-left: 6px; }
QLabel#ReferenceThumb {
    background: $card; border: 1px solid $border; border-radius: 6px;
}

QGroupBox {
    background: $card; border: 1px solid $border; border-radius: 8px;
    margin-top: 10px; padding: 12px 10px 10px 10px; font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 7px; color: $text;
}
QLineEdit, QComboBox, QSpinBox {
    background: $card; color: $text; border: 1px solid $border; border-radius: 7px;
    padding: 5px 8px; min-height: 24px;
    selection-background-color: $primary; selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: $primary; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url($arrow_down); width: 10px; height: 6px; }
QComboBox QAbstractItemView {
    background: $card; color: $text; selection-background-color: $primary;
    selection-color: #ffffff; border: 1px solid $border;
}
QSpinBox::up-button, QSpinBox::down-button {
    border: none; background: transparent; width: 16px;
}
QSpinBox::up-arrow { image: url($arrow_up); width: 8px; height: 5px; }
QSpinBox::down-arrow { image: url($arrow_down); width: 8px; height: 5px; }

QScrollArea#SettingsScroll { background: transparent; border: none; }
QWidget#SettingsContent, QWidget#SettingsPage { background: transparent; }
QCheckBox { spacing: 8px; color: $text; }
QCheckBox::indicator {
    width: 34px; height: 18px; border-radius: 9px; background: $border;
}
QCheckBox::indicator:checked { background: $success; }

QTabWidget::pane {
    border: 1px solid $border; border-radius: 8px; background: $card; top: -1px;
}
QTabBar::tab {
    background: transparent; color: $text_secondary; border: none;
    padding: 7px 12px; margin-right: 3px;
}
QTabBar::tab:selected { color: $primary; border-bottom: 2px solid $primary; }
QTableWidget {
    background: $card; color: $text; gridline-color: $border_light; border: none;
    selection-background-color: $selection_bg; selection-color: $text;
}
QTableWidget::item { padding: 5px; }
QHeaderView::section {
    background: $card_alt; color: $text_secondary; border: none;
    border-bottom: 1px solid $border; padding: 7px 8px; font-weight: 600;
}
QTextEdit[readOnly="true"] {
    font-family: "Cascadia Code", "Consolas", monospace; font-size: 9pt;
    color: $log_text; background: $log_bg; border: 1px solid $border;
}
QGraphicsView#LightboxView, QGraphicsView {
    background: $card_alt; border: none; border-radius: 8px;
}
QLabel#LightboxMeta { color: $text_secondary; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical {
    background: $scrollbar; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: $scrollbar_hover; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle:horizontal {
    background: $scrollbar; border-radius: 5px; min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QMenu {
    background: $card; color: $text; border: 1px solid $border;
    border-radius: 6px; padding: 4px 0;
}
QMenu::item { padding: 7px 24px; }
QMenu::item:selected { background: $selection_bg; color: $text; }
QToolTip {
    background: $card; color: $text; border: 1px solid $border; padding: 4px 8px;
}
QFrame#InputBar {
    background: $card; border: 1px solid $border; border-radius: 18px;
}
QFrame#ParameterChip { background: transparent; border: none; }
QLabel#ParameterLabel { color: $text_secondary; font-size: 8pt; }
QComboBox#ParameterValue, QSpinBox#ParameterValue {
    background: $card_alt; color: $text; border: 1px solid transparent;
    border-radius: 9px; padding: 3px 8px; min-height: 23px;
}
QComboBox#ParameterValue:hover, QSpinBox#ParameterValue:hover { border-color: $border; }
QPushButton#ComposerIconButton {
    background: $card_alt; color: $text_secondary; border: 1px solid transparent;
    border-radius: 10px; padding: 7px 10px; min-height: 25px; font-size: 12pt;
}
QPushButton#ComposerIconButton:hover { background: $border; color: $text; }
QPushButton#ComposerClearButton {
    background: transparent; color: $text_secondary; border: none;
    border-radius: 8px; padding: 6px 9px; min-height: 24px;
}
QPushButton#ComposerClearButton:hover { background: $border; color: $danger; }
QPushButton#GenerateButton {
    background: $text; color: $bg; border: none; border-radius: 10px;
    min-width: 36px; min-height: 36px; padding: 4px 10px; font-size: 15pt; font-weight: 700;
}
QPushButton#GenerateButton:hover { background: #FFFFFF; }
QFrame#GalleryCard { background: transparent; border: 1px solid transparent; border-radius: 12px; }
QFrame#GalleryCard:hover { background: $card; border-color: $border; }
QLabel#GalleryThumb { background: $card_alt; border-radius: 10px; }
QLabel#GalleryCardName { color: $text_secondary; padding: 3px 3px 0; font-size: 8pt; }
QLabel#GalleryEmptyState { color: $text_secondary; background: transparent; font-size: 10pt; }
QLabel#ReferenceThumb { background: $card_alt; border: 1px solid $border; border-radius: 8px; }
QLabel#ReferenceThumb[hasMask="true"] { border: 2px solid $primary; }
QMessageBox, QInputDialog, QDialog { background: $bg; }
""")


def get_qss(theme_name):
    palette = THEMES.get(theme_name, THEMES["米黄"])
    arrows = _generate_arrows(palette["text_secondary"], theme_name)
    data = {**palette, **arrows}
    return _QSS_MODERN.substitute(data)
