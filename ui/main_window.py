import os
import gc
import copy
import time
import subprocess
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QFormLayout, QLineEdit, QComboBox, QPushButton,
    QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QLabel, QScrollArea, QCheckBox, QFileDialog, QInputDialog,
    QMessageBox, QDialog, QMenu, QAbstractItemView, QHeaderView,
    QSpinBox, QGridLayout, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsTextItem, QFrame, QStackedWidget,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QMimeData, QRectF
from PySide6.QtGui import QPixmap, QImage, QColor, QGuiApplication, QShortcut, QKeySequence, QAction, QFont, QPainter

from app_info import APP_TITLE
from config.config_mgr import ConfigManager, GenConfig, CONFIG_FILE
from core.task_queue import TaskManager
from core.utils import ImageUtils
from ui.mask_editor import MaskEditorDialog
from ui.themes import get_qss, THEME_NAMES

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setAcceptDrops(True)

        self.cfg_mgr = ConfigManager(CONFIG_FILE)
        self.current_settings = self.cfg_mgr.get_settings()

        self.task_store = {}
        self.gallery_widgets = {}
        self.selected_image_paths = []
        self.selected_mask_path = None
        self.current_preview_path = None
        self.current_api_type = "gemini"

        self.ratio_map = {
            "1:1 (正方形)": "1:1",
            "4:5 (社交媒体)": "4:5", "3:4 (常规竖屏)": "3:4",
            "2:3 (经典人像)": "2:3", "9:16 (手机壁纸)": "9:16",
            "4:3 (常规横屏)": "4:3", "16:9 (电脑宽屏)": "16:9",
            "21:9 (电影宽屏)": "21:9"
        }
        self.gpt_size_options = [
            "auto (默认)", "1024x1024 (正方形)", "1536x1024 (横版)", "1024x1536 (竖版)",
            "2048x2048 (2K正方形)", "2048x1152 (2K横版)", "1152x2048 (2K竖版)",
            "3840x2160 (4K横版)", "2160x3840 (4K竖版)"
        ]
        self.gpt_size_map = {
            "auto (默认)": "auto", "1024x1024 (正方形)": "1024x1024",
            "1536x1024 (横版)": "1536x1024", "1024x1536 (竖版)": "1024x1536",
            "2048x2048 (2K正方形)": "2048x2048", "2048x1152 (2K横版)": "2048x1152",
            "1152x2048 (2K竖版)": "1152x2048",
            "3840x2160 (4K横版)": "3840x2160", "2160x3840 (4K竖版)": "2160x3840"
        }
        self.gpt_quality_options = ["auto (默认)", "low", "medium", "high"]
        self.gpt_quality_map = {"auto (默认)": "auto", "low": "low", "medium": "medium", "high": "high"}
        self.gpt_format_options = ["PNG", "JPEG", "WebP"]
        self.gpt_format_map = {"PNG": "png", "JPEG": "jpeg", "WebP": "webp"}
        self.gpt_moderation_options = ["auto", "low"]

        saved_workers = self.current_settings.get("max_workers", 1)
        self.task_manager = TaskManager(max_workers=saved_workers)
        self.task_manager.task_added.connect(self.on_task_added)
        self.task_manager.task_updated.connect(self.on_task_updated)
        self.task_manager.log_message.connect(self.log)

        self._init_window_geometry()
        self._build_ui()
        self._refresh_profile_ui()
        self._refresh_prompt_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(1000)

        QShortcut(QKeySequence("Ctrl+Return"), self, self.on_enqueue_task)
        QShortcut(QKeySequence("Ctrl+V"), self, self._paste_from_clipboard)

    def _init_window_geometry(self):
        self.setMinimumSize(1200, 750)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        saved_idx = self.current_settings.get("window_size_idx", -1)
        self.resolution_options = [
            (1200, 750, "1200x750 (Laptop)"),
            (1600, 900, "1600x900"),
            (1920, 1080, "1920x1080")
        ]
        if 0 <= saved_idx < len(self.resolution_options):
            w, h = self.resolution_options[saved_idx][:2]
        elif screen.width() > 1920:
            w, h = 1600, 900
        else:
            w, h = 1200, 750
        self.resize(w, h)
        self.move((screen.width() - w) // 2, (screen.height() - h) // 2)

    # ========== UI Construction ==========

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("AppSurface")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("AppHeader")
        header.setFixedHeight(58)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 0, 18, 0)
        header_layout.setSpacing(8)

        brand = QFrame()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 12, 0)
        brand_layout.setSpacing(0)
        brand_title = QLabel("GNBP Image Playground")
        brand_title.setObjectName("BrandTitle")
        brand_layout.addWidget(brand_title)
        brand_subtitle = QLabel("LOCAL DESKTOP CLIENT")
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_layout.addWidget(brand_subtitle)
        header_layout.addWidget(brand)

        header_layout.addStretch(1)

        mode_switch = QFrame()
        mode_switch.setObjectName("HeaderModeSwitch")
        mode_layout = QHBoxLayout(mode_switch)
        mode_layout.setContentsMargins(3, 3, 3, 3)
        mode_layout.setSpacing(2)
        self.btn_gallery = QPushButton("画廊")
        self.btn_gallery.setObjectName("HeaderNavButton")
        self.btn_gallery.setCheckable(True)
        self.btn_gallery.setChecked(True)
        self.btn_gallery.setToolTip("显示历史图库")
        self.btn_gallery.clicked.connect(self._close_side_panel)
        mode_layout.addWidget(self.btn_gallery)

        self.btn_tasks = QPushButton("任务")
        self.btn_tasks.setObjectName("HeaderNavButton")
        self.btn_tasks.setCheckable(True)
        self.btn_tasks.setToolTip("查看任务队列和运行日志")
        self.btn_tasks.clicked.connect(self._toggle_task_panel)
        mode_layout.addWidget(self.btn_tasks)
        header_layout.addWidget(mode_switch)

        self.header_status = QLabel("就绪")
        self.header_status.setObjectName("HeaderStatus")
        header_layout.addWidget(self.header_status)

        self.profile_combo = QComboBox()
        self.profile_combo.setObjectName("ProfileChip")
        self.profile_combo.setMinimumWidth(154)
        self.profile_combo.setMaximumWidth(220)
        self.profile_combo.setToolTip("切换 API 配置")
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        header_layout.addWidget(self.profile_combo)

        self.btn_api_toggle = QPushButton("⚙")
        self.btn_api_toggle.setObjectName("HeaderToolButton")
        self.btn_api_toggle.setFixedSize(36, 36)
        self.btn_api_toggle.setToolTip("设置 API、模型和行为")
        self.btn_api_toggle.clicked.connect(self._toggle_api_panel)
        header_layout.addWidget(self.btn_api_toggle)

        root_layout.addWidget(header)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("ContentSplitter")
        self.splitter.setHandleWidth(0)
        root_layout.addWidget(self.splitter, 1)

        main_widget = QWidget()
        main_widget.setObjectName("MainWorkspace")
        self.right_layout = QVBoxLayout(main_widget)
        self.right_layout.setContentsMargins(18, 12, 18, 12)
        self.right_layout.setSpacing(10)
        self.splitter.addWidget(main_widget)

        self.side_panel = QFrame()
        self.side_panel.setObjectName("SidePanel")
        self.side_panel.setMinimumWidth(330)
        self.side_panel.setMaximumWidth(440)
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(16, 16, 16, 16)
        side_layout.setSpacing(12)

        side_header = QHBoxLayout()
        self.side_title_label = QLabel("设置")
        self.side_title_label.setObjectName("SidePanelTitle")
        side_header.addWidget(self.side_title_label)
        side_header.addStretch()
        self.btn_side_close = QPushButton("×")
        self.btn_side_close.setObjectName("IconButton")
        self.btn_side_close.setFixedSize(30, 30)
        self.btn_side_close.setToolTip("关闭面板")
        self.btn_side_close.clicked.connect(self._close_side_panel)
        side_header.addWidget(self.btn_side_close)
        side_layout.addLayout(side_header)

        self.side_stack = QStackedWidget()
        self.side_stack.setObjectName("SideStack")
        side_layout.addWidget(self.side_stack, 1)
        self.splitter.addWidget(self.side_panel)

        settings_page = QWidget()
        settings_page.setObjectName("SettingsPage")
        settings_page_layout = QVBoxLayout(settings_page)
        settings_page_layout.setContentsMargins(0, 0, 0, 0)
        settings_page_layout.setSpacing(0)
        settings_scroll = QScrollArea()
        settings_scroll.setObjectName("SettingsScroll")
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        settings_content = QWidget()
        settings_content.setObjectName("SettingsContent")
        self.left_layout = QVBoxLayout(settings_content)
        self.left_layout.setContentsMargins(2, 2, 6, 10)
        self.left_layout.setSpacing(12)
        settings_scroll.setWidget(settings_content)
        settings_page_layout.addWidget(settings_scroll)
        self.settings_page = settings_page
        self.side_stack.addWidget(settings_page)

        self.splitter.setSizes([1600, 0])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.side_panel.setVisible(False)

        self._build_preview_section()
        self._build_prompt_section()
        self._build_api_section()
        self._build_settings_section()
        self._build_action_section()
        self._build_notebook_section()
        self._load_history()

    # --- API Section ---
    def _build_api_section(self):
        self.api_detail_group = QGroupBox("API 连接")
        form = QFormLayout(self.api_detail_group)
        form.setContentsMargins(12, 16, 12, 12)
        form.setSpacing(9)

        hint = QLabel("请求从本机直接发送，配置会按当前配置名保存。")
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        form.addRow(hint)

        self.api_url_entry = QLineEdit()
        self.api_url_entry.setPlaceholderText("例如 https://aihub.top/v1")
        form.addRow("API URL", self.api_url_entry)

        key_row = QHBoxLayout()
        self.api_key_entry = QLineEdit()
        self.api_key_entry.setEchoMode(QLineEdit.Password)
        self.api_key_entry.setPlaceholderText("粘贴 API Key")
        key_row.addWidget(self.api_key_entry)
        self.btn_eye = QPushButton("显示")
        self.btn_eye.setObjectName("InlineButton")
        self.btn_eye.setFixedWidth(48)
        self.btn_eye.setToolTip("显示或隐藏 API Key")
        self.btn_eye.clicked.connect(self._toggle_key_view)
        key_row.addWidget(self.btn_eye)
        form.addRow("API Key", key_row)

        self.model_entry = QLineEdit()
        self.model_entry.setPlaceholderText("例如 gpt-image-1")
        form.addRow("模型", self.model_entry)

        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["Gemini", "GPT / OpenAI"])
        self.api_type_combo.currentIndexChanged.connect(self._on_api_type_changed)
        form.addRow("协议", self.api_type_combo)

        self.api_mode_combo = QComboBox()
        self.api_mode_combo.addItem("Images API (/v1/images)", "images")
        self.api_mode_combo.addItem("Responses API (/v1/responses)", "responses")
        self.api_mode_combo.setToolTip("Responses API 需要支持 image_generation 工具的模型")
        self.api_mode_label = QLabel("API 接口")
        form.addRow(self.api_mode_label, self.api_mode_combo)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("新建配置")
        btn_new.setObjectName("GhostButton")
        btn_new.clicked.connect(self._create_new_profile)
        btn_row.addWidget(btn_new)
        btn_del = QPushButton("删除")
        btn_del.setObjectName("DangerButton")
        btn_del.clicked.connect(self._delete_current_profile)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_save = QPushButton("保存")
        btn_save.setObjectName("PrimarySmallButton")
        btn_save.clicked.connect(self._save_profile_changes)
        btn_row.addWidget(btn_save)
        form.addRow(btn_row)

        self.api_detail_group.setVisible(True)
        self.left_layout.addWidget(self.api_detail_group)

    # --- Prompt Section ---
    def _build_prompt_section(self):
        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.addStretch(1)

        composer = QFrame()
        composer.setObjectName("InputBar")
        composer.setMinimumWidth(560)
        composer.setMaximumWidth(980)
        layout = QVBoxLayout(composer)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(9)

        self.ref_scroll = QScrollArea()
        self.ref_scroll.setObjectName("AttachmentScroll")
        self.ref_scroll.setWidgetResizable(True)
        self.ref_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ref_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ref_scroll.setFixedHeight(70)
        self.ref_inner = QWidget()
        self.ref_inner.setObjectName("AttachmentSurface")
        self.ref_inner_layout = QHBoxLayout(self.ref_inner)
        self.ref_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.ref_inner_layout.setSpacing(7)
        self.ref_scroll.setWidget(self.ref_inner)
        self.ref_scroll.setVisible(False)
        layout.addWidget(self.ref_scroll)

        self.prompt_text = QTextEdit()
        self.prompt_text.setObjectName("PromptInput")
        self.prompt_text.setPlaceholderText("描述你想生成的图片，可输入 @ 来指定参考图...")
        self.prompt_text.setMinimumHeight(46)
        self.prompt_text.setMaximumHeight(92)
        self.prompt_text.textChanged.connect(self._update_char_count)
        layout.addWidget(self.prompt_text)

        controls = QHBoxLayout()
        controls.setSpacing(7)

        self.prompt_combo = QComboBox()
        self.prompt_combo.setObjectName("PresetCombo")
        self.prompt_combo.setMinimumWidth(126)
        self.prompt_combo.setMaximumWidth(180)
        self.prompt_combo.setToolTip("选择已保存的提示词")
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_selected)
        controls.addWidget(self.prompt_combo)

        self.prompt_save_btn = QPushButton("保存")
        self.prompt_save_btn.setObjectName("ComposerClearButton")
        self.prompt_save_btn.setToolTip("更新当前提示词")
        self.prompt_save_btn.clicked.connect(self._update_current_prompt)
        controls.addWidget(self.prompt_save_btn)
        self.prompt_save_as_btn = QPushButton("另存")
        self.prompt_save_as_btn.setObjectName("ComposerClearButton")
        self.prompt_save_as_btn.setToolTip("另存为新的提示词")
        self.prompt_save_as_btn.clicked.connect(self._save_as_new_prompt)
        controls.addWidget(self.prompt_save_as_btn)
        self.prompt_delete_btn = QPushButton("删除")
        self.prompt_delete_btn.setObjectName("ComposerClearButton")
        self.prompt_delete_btn.setToolTip("删除当前提示词")
        self.prompt_delete_btn.clicked.connect(self._delete_current_prompt)
        controls.addWidget(self.prompt_delete_btn)

        self.lbl_char_count = QLabel("0 字")
        self.lbl_char_count.setObjectName("CharCount")
        controls.addWidget(self.lbl_char_count)
        controls.addStretch(1)

        def add_parameter_chip(label_text, widget):
            chip = QFrame()
            chip.setObjectName("ParameterChip")
            chip_layout = QVBoxLayout(chip)
            chip_layout.setContentsMargins(0, 0, 0, 0)
            chip_layout.setSpacing(1)
            label = QLabel(label_text)
            label.setObjectName("ParameterLabel")
            chip_layout.addWidget(label)
            widget.setObjectName("ParameterValue")
            widget.setMinimumHeight(27)
            chip_layout.addWidget(widget)
            controls.addWidget(chip)
            return chip, label

        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(self.gpt_size_options)
        self.param1_chip, self.param1_label = add_parameter_chip("尺寸", self.ratio_combo)

        self.res_combo = QComboBox()
        self.res_combo.addItems(self.gpt_quality_options)
        self.param2_chip, self.param2_label = add_parameter_chip("画质", self.res_combo)

        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(self.gpt_format_options)
        self.output_format_combo.currentTextChanged.connect(self._refresh_compression_state)
        self.output_format_chip, self.output_format_label = add_parameter_chip("格式", self.output_format_combo)

        self.moderation_combo = QComboBox()
        self.moderation_combo.addItems(self.gpt_moderation_options)
        self.moderation_chip, self.moderation_label = add_parameter_chip("审核", self.moderation_combo)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 99)
        self.batch_spin.setValue(self.current_settings.get("batch_count", 1))
        self.batch_spin.valueChanged.connect(self._on_batch_count_changed)
        self.batch_chip, self.batch_label = add_parameter_chip("数量", self.batch_spin)

        self.compression_spin = QSpinBox()
        self.compression_spin.setRange(0, 100)
        self.compression_spin.setSuffix("%")
        self.compression_spin.setValue(self.current_settings.get("output_compression", 0))
        self.compression_spin.valueChanged.connect(self._refresh_compression_state)
        self.compression_chip, self.compression_label = add_parameter_chip("压缩", self.compression_spin)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setObjectName("ComposerIconButton")
        self.attach_btn.setFixedSize(38, 36)
        self.attach_btn.setToolTip("上传参考图，也可以直接拖入窗口")
        self.attach_btn.clicked.connect(self._select_images)
        controls.addWidget(self.attach_btn)

        self.clear_images_btn = QPushButton("×")
        self.clear_images_btn.setObjectName("ComposerClearButton")
        self.clear_images_btn.setFixedSize(28, 34)
        self.clear_images_btn.setToolTip("清空参考图")
        self.clear_images_btn.clicked.connect(self._clear_images)
        self.clear_images_btn.setVisible(False)
        controls.addWidget(self.clear_images_btn)

        self.gen_btn = QPushButton("→")
        self.gen_btn.setObjectName("GenerateButton")
        self.gen_btn.setFixedSize(42, 36)
        self.gen_btn.setToolTip("生成图像")
        self.gen_btn.clicked.connect(self.on_enqueue_task)
        controls.addWidget(self.gen_btn)
        self.prompt_button_layout = controls
        layout.addLayout(controls)

        # Legacy fields remain available to the task/API layer, but the standalone
        # file-mask picker is intentionally removed from the primary composer.
        self.ref_count_label = QLabel("0 张")
        self.ref_count_label.setObjectName("AttachmentCount")
        self.mask_edit_btn = QPushButton("编辑遮罩")
        self.clear_mask_btn = QPushButton("清除")
        self.mask_label = QLabel("未设置遮罩")
        for legacy_widget in (self.mask_edit_btn, self.clear_mask_btn, self.mask_label, self.ref_count_label):
            legacy_widget.setVisible(False)
        self.mask_edit_btn.clicked.connect(self._edit_mask)
        self.clear_mask_btn.clicked.connect(self._clear_mask)
        self.mask_label.setToolTip("遮罩会作为 mask 字段上传，并要求至少有一张参考图")

        shell_layout.addWidget(composer)
        shell_layout.addStretch(1)
        self.right_layout.addWidget(shell)

    # --- Settings Section ---
    def _build_settings_section(self):
        param_group = QGroupBox("生成参数")
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(12, 16, 12, 12)
        param_layout.setSpacing(8)
        param_hint = QLabel("尺寸、画质、格式和数量可直接在底部输入栏调整。")
        param_hint.setObjectName("SectionHint")
        param_hint.setWordWrap(True)
        param_layout.addWidget(param_hint)

        worker_row = QHBoxLayout()
        worker_row.addWidget(QLabel("最大并发"))
        self.worker_spin = QSpinBox()
        self.worker_spin.setRange(1, 8)
        self.worker_spin.setValue(self.current_settings.get("max_workers", 1))
        self.worker_spin.valueChanged.connect(self._on_worker_count_changed)
        self.worker_spin.setObjectName("ParameterValue")
        self.worker_spin.setMaximumWidth(120)
        worker_row.addWidget(self.worker_spin)
        worker_row.addStretch(1)
        param_layout.addLayout(worker_row)
        self.left_layout.addWidget(param_group)


    # --- Action Section ---
    def _build_action_section(self):
        behavior_group = QGroupBox("保存与行为")
        behavior_layout = QGridLayout(behavior_group)
        behavior_layout.setContentsMargins(12, 16, 12, 12)
        behavior_layout.setSpacing(8)

        behavior_layout.addWidget(QLabel("输出目录"), 0, 0)
        self.output_dir_entry = QLineEdit(self.current_settings.get("output_dir", "images"))
        self.output_dir_entry.setPlaceholderText("images 或 D:/Generated")
        behavior_layout.addWidget(self.output_dir_entry, 0, 1, 1, 2)
        browse_output_btn = QPushButton("浏览")
        browse_output_btn.setObjectName("GhostButton")
        browse_output_btn.clicked.connect(self._choose_output_dir)
        behavior_layout.addWidget(browse_output_btn, 0, 3)

        behavior_layout.addWidget(QLabel("窗口尺寸"), 1, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItems([opt[2] for opt in self.resolution_options])
        saved_idx = self.current_settings.get("window_size_idx", 1)
        self.size_combo.setCurrentIndex(min(saved_idx, len(self.resolution_options) - 1))
        self.size_combo.currentIndexChanged.connect(self._change_window_size)
        behavior_layout.addWidget(self.size_combo, 1, 1)

        behavior_layout.addWidget(QLabel("主题"), 1, 2)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_NAMES)
        saved_theme = self.current_settings.get("theme", "Playground Dark")
        if saved_theme == "米黄":
            saved_theme = "Playground Dark"
        if saved_theme in THEME_NAMES:
            self.theme_combo.setCurrentText(saved_theme)
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        behavior_layout.addWidget(self.theme_combo, 1, 3)

        self.show_preview_cb = QCheckBox("生成后自动选中")
        self.show_preview_cb.setChecked(self.current_settings.get("show_preview", True))
        self.show_preview_cb.stateChanged.connect(self._toggle_preview_visibility)
        behavior_layout.addWidget(self.show_preview_cb, 2, 0, 1, 2)

        self.sound_cb = QCheckBox("完成提示音")
        self.sound_cb.setChecked(self.current_settings.get("sound_notify", True))
        self.sound_cb.stateChanged.connect(self._on_sound_toggle)
        behavior_layout.addWidget(self.sound_cb, 2, 2, 1, 2)

        behavior_layout.setColumnStretch(1, 1)
        behavior_layout.setColumnStretch(3, 1)
        self.left_layout.addWidget(behavior_group)

        util_row = QHBoxLayout()
        for text, slot in [("打开输出目录", self._open_output_dir),
                           ("清理已完成", self._clear_completed_tasks),
                           ("清理内存", self._cleanup_memory)]:
            btn = QPushButton(text)
            btn.setObjectName("GhostButton")
            btn.clicked.connect(slot)
            util_row.addWidget(btn)
        util_box = QWidget()
        util_box.setLayout(util_row)
        self.left_layout.addWidget(util_box)
        self.left_layout.addStretch(1)

    # --- Notebook (Task List + Log) ---
    def _build_notebook_section(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("TaskTabs")

        # Tab 1: Task Table
        q_tab = QWidget()
        q_layout = QVBoxLayout(q_tab)
        q_layout.setContentsMargins(0, 4, 0, 0)

        self.task_table = QTableWidget(0, 6)
        self.task_table.setHorizontalHeaderLabels(["ID", "状态", "参数", "耗时", "提示词", "操作"])
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(42)
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self._show_context_menu)
        self.task_table.selectionModel().selectionChanged.connect(self._on_task_select)
        self.task_table.setWordWrap(False)
        self.task_table.setTextElideMode(Qt.ElideRight)

        header = self.task_table.horizontalHeader()
        header.resizeSection(0, 60)
        header.resizeSection(1, 90)
        header.resizeSection(2, 110)
        header.resizeSection(3, 60)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.resizeSection(5, 110)

        q_layout.addWidget(self.task_table)
        self.tab_widget.addTab(q_tab, "任务队列")

        # Tab 2: Log
        l_tab = QWidget()
        l_layout = QVBoxLayout(l_tab)
        l_layout.setContentsMargins(0, 4, 0, 0)

        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()
        btn_clear_log = QPushButton("清除日志")
        btn_clear_log.setObjectName("InlineButton")
        btn_clear_log.clicked.connect(lambda: self.log_text.clear())
        log_toolbar.addWidget(btn_clear_log)
        l_layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        l_layout.addWidget(self.log_text)
        self.tab_widget.addTab(l_tab, "运行日志")

        self.side_stack.addWidget(self.tab_widget)

    # --- Right Side: Preview + Gallery ---
    def _build_preview_section(self):
        self.preview_scene = QGraphicsScene(self)
        self.preview_view = QGraphicsView(self.preview_scene)
        self.preview_view.setMinimumHeight(200)
        self.preview_view.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.preview_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.preview_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.preview_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview_view.wheelEvent = self._preview_wheel_event
        self.preview_view.mouseDoubleClickEvent = lambda e: self._open_preview()
        self.preview_view.setVisible(False)

        self._preview_placeholder = self.preview_scene.addText(
            "No Image", QFont("Segoe UI", 14)
        )
        self._preview_placeholder.setDefaultTextColor(QColor("#999999"))
        self._preview_pixmap_item = None
        self._zoom_level = 1.0

        self.gallery_favorites = set()
        self.gallery_task_ids = {}

        search_surface = QFrame()
        search_surface.setObjectName("SearchBarSurface")
        search_row = QHBoxLayout(search_surface)
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)

        self.favorite_filter_btn = QPushButton("☆")
        self.favorite_filter_btn.setObjectName("FavoriteFilterButton")
        self.favorite_filter_btn.setCheckable(True)
        self.favorite_filter_btn.setFixedSize(40, 36)
        self.favorite_filter_btn.setToolTip("只显示收藏图片")
        self.favorite_filter_btn.clicked.connect(self._toggle_gallery_favorites)
        search_row.addWidget(self.favorite_filter_btn)

        self.search_filter_combo = QComboBox()
        self.search_filter_combo.setObjectName("FilterButton")
        self.search_filter_combo.setMinimumWidth(92)
        self.search_filter_combo.addItem("全部", "all")
        self.search_filter_combo.addItem("已完成", "done")
        self.search_filter_combo.addItem("生成中", "running")
        self.search_filter_combo.addItem("失败", "error")
        self.search_filter_combo.currentIndexChanged.connect(self._filter_gallery)
        search_row.addWidget(self.search_filter_combo)

        self.search_entry = QLineEdit()
        self.search_entry.setObjectName("SearchInput")
        self.search_entry.setPlaceholderText("搜索提示词、参数...")
        self.search_entry.textChanged.connect(self._filter_gallery)
        search_row.addWidget(self.search_entry, 1)

        self.gallery_count_label = QLabel("0 张")
        self.gallery_count_label.setObjectName("GalleryMeta")
        search_row.addWidget(self.gallery_count_label)
        self.right_layout.addWidget(search_surface)

        self.meta_label = QLabel("选择图片查看详情")
        self.meta_label.setObjectName("GalleryMeta")
        self.meta_label.setVisible(False)

        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setObjectName("GalleryScroll")
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.gallery_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.gallery_inner = QWidget()
        self.gallery_inner.setObjectName("GallerySurface")
        self.gallery_inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gallery_inner_layout = QGridLayout(self.gallery_inner)
        self.gallery_inner_layout.setContentsMargins(2, 2, 2, 18)
        self.gallery_inner_layout.setHorizontalSpacing(12)
        self.gallery_inner_layout.setVerticalSpacing(12)
        self.gallery_inner_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.gallery_scroll.setWidget(self.gallery_inner)
        self.right_layout.addWidget(self.gallery_scroll, 1)

        self.gallery_order = []
        self.gallery_empty_label = QLabel("输入提示词开始生成图片")
        self.gallery_empty_label.setObjectName("GalleryEmptyState")
        self.gallery_empty_label.setAlignment(Qt.AlignCenter)
        self.gallery_empty_label.setMinimumHeight(260)
        self.gallery_empty_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._relayout_gallery()

    # ========== Logic ==========

    def _show_side_panel(self, page, title):
        self.side_stack.setCurrentWidget(page)
        self.side_title_label.setText(title)
        self.side_panel.setVisible(True)
        self.btn_gallery.setChecked(False)
        self.btn_api_toggle.setChecked(page is self.settings_page)
        self.btn_tasks.setChecked(page is self.tab_widget)

    def _close_side_panel(self, *_args):
        self.side_panel.setVisible(False)
        self.btn_gallery.setChecked(True)
        self.btn_tasks.setChecked(False)

    def _toggle_api_panel(self, _checked=False):
        self._open_settings_dialog()

    def _toggle_task_panel(self, _checked=False):
        self._open_tasks_dialog()

    def _open_settings_dialog(self):
        dialog = getattr(self, "_settings_dialog", None)
        if dialog is None:
            dialog = QDialog(self)
            dialog.setObjectName("SettingsDialog")
            dialog.setWindowTitle("设置")
            dialog.setModal(False)
            dialog.setMinimumSize(520, 620)
            dialog.resize(560, 760)
            dialog_layout = QVBoxLayout(dialog)
            dialog_layout.setContentsMargins(18, 16, 18, 16)
            dialog_layout.setSpacing(0)
            self.side_stack.removeWidget(self.settings_page)
            self.settings_page.setParent(dialog)
            dialog_layout.addWidget(self.settings_page)
            self.settings_page.show()
            dialog.finished.connect(lambda _result: self._close_side_panel())
            self._settings_dialog = dialog

        self.btn_gallery.setChecked(False)
        self.btn_tasks.setChecked(False)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _open_tasks_dialog(self):
        dialog = getattr(self, "_tasks_dialog", None)
        if dialog is None:
            dialog = QDialog(self)
            dialog.setObjectName("TasksDialog")
            dialog.setWindowTitle("任务与日志")
            dialog.setModal(False)
            dialog.setMinimumSize(760, 480)
            dialog.resize(980, 620)
            dialog_layout = QVBoxLayout(dialog)
            dialog_layout.setContentsMargins(14, 14, 14, 14)
            self.side_stack.removeWidget(self.tab_widget)
            self.tab_widget.setParent(dialog)
            dialog_layout.addWidget(self.tab_widget)
            self.tab_widget.show()
            dialog.finished.connect(lambda _result: self._close_side_panel())
            self._tasks_dialog = dialog

        self.btn_gallery.setChecked(False)
        self.btn_tasks.setChecked(True)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _toggle_key_view(self):
        if self.api_key_entry.echoMode() == QLineEdit.Password:
            self.api_key_entry.setEchoMode(QLineEdit.Normal)
            self.btn_eye.setText("隐藏")
        else:
            self.api_key_entry.setEchoMode(QLineEdit.Password)
            self.btn_eye.setText("显示")

    def log(self, msg):
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{ts} {msg}")

    # --- Task Queue ---
    def on_enqueue_task(self):
        prompt = self.prompt_text.toPlainText().strip()
        key = self.api_key_entry.text().strip()
        api_url = self.api_url_entry.text().strip()
        model = self.model_entry.text().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "Prompt 不能为空")
            return
        if not key:
            QMessageBox.warning(self, "提示", "API Key 不能为空")
            return
        if not api_url:
            QMessageBox.warning(self, "提示", "API 地址不能为空")
            return
        if not model:
            QMessageBox.warning(self, "提示", "模型名称不能为空")
            return

        out_dir = self.output_dir_entry.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "输出目录不能为空")
            return
        self.cfg_mgr.data.setdefault("settings", {})["output_dir"] = out_dir
        self.cfg_mgr.save_data()
        batch_count = self.batch_spin.value()

        if self.current_api_type == "gpt":
            self.cfg_mgr.update_settings(
                self.current_settings.get("aspect_ratio_idx", 1),
                self.current_settings.get("resolution_idx", 2),
                out_dir,
                gpt_size_idx=self.ratio_combo.currentIndex(),
                gpt_quality_idx=self.res_combo.currentIndex(),
                output_format_idx=self.output_format_combo.currentIndex(),
                moderation_idx=self.moderation_combo.currentIndex(),
                output_compression=self.compression_spin.value(),
            )
            size_text = self.ratio_combo.currentText()
            quality_text = self.res_combo.currentText()
            output_format = self.gpt_format_map.get(self.output_format_combo.currentText(), "png")
            moderation = self.moderation_combo.currentText()
            output_compression = self.compression_spin.value() or None
            if self.selected_mask_path and not self.selected_image_paths:
                QMessageBox.warning(self, "提示", "使用遮罩前请先添加至少一张参考图")
                return
        elif self.selected_mask_path:
            QMessageBox.warning(self, "提示", "Gemini 接口不支持当前的 mask 遮罩，请切换到 GPT 或清除遮罩")
            return
        else:
            self.cfg_mgr.update_settings(
                self.ratio_combo.currentIndex(), self.res_combo.currentIndex(), out_dir
            )
            ratio_text = self.ratio_combo.currentText()

        for _ in range(batch_count):
            if self.current_api_type == "gpt":
                cfg = GenConfig(
                    api_url=api_url,
                    api_key=key, model=model,
                    prompt=prompt, aspect_ratio="", resolution="",
                    output_dir=out_dir, api_type="gpt",
                    api_mode=self.api_mode_combo.currentData() or "images",
                    ref_images=copy.copy(self.selected_image_paths),
                    mask_image=self.selected_mask_path,
                    size=self.gpt_size_map.get(size_text, "auto"),
                    quality=self.gpt_quality_map.get(quality_text, "auto"),
                    output_format=output_format,
                    output_compression=output_compression,
                    moderation=moderation,
                )
            else:
                cfg = GenConfig(
                    api_url=api_url,
                    api_key=key, model=model,
                    prompt=prompt,
                    aspect_ratio=self.ratio_map.get(ratio_text, "3:4"),
                    resolution=self.res_combo.currentText(),
                    output_dir=out_dir, api_type="gemini",
                    ref_images=copy.copy(self.selected_image_paths)
                )

            self.task_manager.add_task(cfg)

        self.log(f"📥 已加入 {batch_count} 个任务")

    def on_task_added(self, data):
        tid = data["id"]
        self.task_store[tid] = data
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)
        self.task_table.setItem(row, 0, QTableWidgetItem(tid))
        self.task_table.setItem(row, 1, QTableWidgetItem(data["status"]))
        self.task_table.setItem(row, 2, QTableWidgetItem(data.get("params_short", "")))
        self.task_table.setItem(row, 3, QTableWidgetItem("--"))
        self.task_table.setItem(row, 4, QTableWidgetItem(data["prompt_short"]))
        self._add_ops_buttons(row, tid)

    def _add_ops_buttons(self, row, tid):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        btn_copy = QPushButton("重试")
        btn_copy.setProperty("cssClass", "table-action")
        btn_copy.setFixedSize(42, 22)
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.clicked.connect(lambda: self._retry_task(tid))
        layout.addWidget(btn_copy)

        btn_del = QPushButton("删除")
        btn_del.setProperty("cssClass", "table-action-danger")
        btn_del.setFixedSize(42, 22)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.clicked.connect(lambda: self._delete_task(tid))
        layout.addWidget(btn_del)

        self.task_table.setCellWidget(row, 5, widget)

    def on_task_updated(self, data):
        tid = data["id"]
        if tid in self.task_store:
            self.task_store[tid].update(data)

        for row in range(self.task_table.rowCount()):
            item = self.task_table.item(row, 0)
            if item and item.text() == tid:
                self.task_table.setItem(row, 1, QTableWidgetItem(data["status"]))
                if "duration_str" in data:
                    self.task_table.setItem(row, 3, QTableWidgetItem(data["duration_str"]))

                status = data["status"]
                color_map = {"Success": "#2E7D32", "Failed": "#C62828", "Error": "#C62828"}
                color = color_map.get(status, "#1565C0" if "Running" in status else "#333333")
                for col in range(5):
                    cell = self.task_table.item(row, col)
                    if cell:
                        cell.setForeground(QColor(color))

                paths = data.get("paths") or ([data["path"]] if data.get("path") else [])
                if paths:
                    self._show_preview(paths[0])
                    for path in paths:
                        self._add_to_gallery(path, tid)

                if status == "Success" and HAS_WINSOUND and self.sound_cb.isChecked():
                    if self._all_tasks_done():
                        try:
                            winsound.MessageBeep(winsound.MB_ICONASTERISK)
                        except Exception:
                            pass

                break

    def _retry_task(self, tid):
        task = self.task_store.get(tid)
        if not task:
            return
        cfg_data = task["config"]
        valid_keys = GenConfig.__dataclass_fields__.keys()
        filtered = {k: v for k, v in cfg_data.items() if k in valid_keys}
        new_cfg = GenConfig(**filtered)
        self.task_manager.add_task(new_cfg)

    def _delete_task(self, tid):
        task = self.task_store.get(tid)
        if task and task.get("status") == "Waiting":
            self.task_manager.cancel_task(tid)
        for row in range(self.task_table.rowCount()):
            item = self.task_table.item(row, 0)
            if item and item.text() == tid:
                self.task_table.removeRow(row)
                break
        paths = task.get("paths", []) if task else []
        if task and task.get("path") and task["path"] not in paths:
            paths = [task["path"], *paths]
        for path in paths:
            widget = self.gallery_widgets.pop(path, None)
            if path in self.gallery_order:
                self.gallery_order.remove(path)
            self.gallery_task_ids.pop(path, None)
            self.gallery_favorites.discard(path)
            if widget:
                widget.deleteLater()
        self._relayout_gallery()
        if tid in self.task_store:
            del self.task_store[tid]

    def _on_task_select(self):
        rows = self.task_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        item = self.task_table.item(row, 0)
        if not item:
            return
        tid = item.text()
        task = self.task_store.get(tid)
        if task:
            cfg = task["config"]
            if cfg.get("api_type") == "gpt":
                self.meta_label.setText(
                    f"Model: {cfg.get('model')} | API: {cfg.get('api_mode', 'images')} | "
                    f"Size: {cfg.get('size')} | "
                    f"Quality: {cfg.get('quality')} | Format: {cfg.get('output_format', 'png')}"
                )
            else:
                self.meta_label.setText(f"Model: {cfg.get('model')} | Ratio: {cfg.get('aspect_ratio')}")
            if task.get("path"):
                self._show_preview(task["path"])

    def _update_timer(self):
        for row in range(self.task_table.rowCount()):
            status_item = self.task_table.item(row, 1)
            id_item = self.task_table.item(row, 0)
            if status_item and id_item and "Running" in status_item.text():
                task = self.task_store.get(id_item.text())
                if task and task.get("start_time"):
                    elapsed = int(time.time() - task["start_time"])
                    self.task_table.setItem(row, 3, QTableWidgetItem(f"{elapsed}s"))

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("📥 读取参数", self._load_params_from_task)
        menu.addAction("📋 复制提示词", self._copy_prompt_from_task)
        menu.addAction("📂 在文件夹中选中", self._reveal_file_in_explorer)
        menu.addSeparator()
        menu.addAction("🧹 清除已完成", self._clear_completed_tasks)
        menu.exec(self.task_table.mapToGlobal(pos))

    def _load_params_from_task(self):
        rows = self.task_table.selectionModel().selectedRows()
        if not rows:
            return
        tid = self.task_table.item(rows[0].row(), 0).text()
        task = self.task_store.get(tid)
        if not task:
            return
        self._apply_config_to_ui(task["config"], include_credentials=True)
        self.log("📋 参数已载入")

    def _apply_config_to_ui(self, cfg, include_credentials=False):
        if cfg.get("prompt"):
            self.prompt_text.setPlainText(cfg["prompt"])
        if cfg.get("model"):
            self.model_entry.setText(cfg["model"])
        if cfg.get("api_url"):
            self.api_url_entry.setText(cfg["api_url"])
        if include_credentials and cfg.get("api_key"):
            self.api_key_entry.setText(cfg["api_key"])
        if cfg.get("output_dir"):
            self.output_dir_entry.setText(cfg["output_dir"])

        api_type = cfg.get("api_type", "gemini")
        self.api_type_combo.setCurrentIndex(1 if api_type == "gpt" else 0)
        self.current_api_type = api_type
        api_mode = cfg.get("api_mode", "images")
        mode_index = self.api_mode_combo.findData(api_mode)
        self.api_mode_combo.setCurrentIndex(max(0, mode_index))
        self._refresh_param_panel()

        if api_type == "gpt":
            size = cfg.get("size", "auto")
            for label, value in self.gpt_size_map.items():
                if value == size:
                    self.ratio_combo.setCurrentText(label)
                    break
            quality = cfg.get("quality", "auto")
            for label, value in self.gpt_quality_map.items():
                if value == quality:
                    self.res_combo.setCurrentText(label)
                    break
            output_format = str(cfg.get("output_format", "png")).lower()
            self.output_format_combo.setCurrentText(
                next((label for label, value in self.gpt_format_map.items() if value == output_format), "PNG")
            )
            self.moderation_combo.setCurrentText(cfg.get("moderation", "auto"))
            try:
                compression = int(cfg.get("output_compression") or 0)
            except (TypeError, ValueError):
                compression = 0
            self.compression_spin.setValue(max(0, min(100, compression)))
        else:
            for label, value in self.ratio_map.items():
                if value == cfg.get("aspect_ratio"):
                    self.ratio_combo.setCurrentText(label)
                    break
            resolution = cfg.get("resolution")
            if resolution in ["1K", "2K", "4K"]:
                self.res_combo.setCurrentText(resolution)

    def _copy_prompt_from_task(self):
        rows = self.task_table.selectionModel().selectedRows()
        if not rows:
            return
        tid = self.task_table.item(rows[0].row(), 0).text()
        task = self.task_store.get(tid)
        if task:
            QGuiApplication.clipboard().setText(task["config"]["prompt"])
            self.log("📋 提示词已复制")

    def _reveal_file_in_explorer(self):
        rows = self.task_table.selectionModel().selectedRows()
        if not rows:
            return
        tid = self.task_table.item(rows[0].row(), 0).text()
        task = self.task_store.get(tid)
        if task and task.get("path") and os.path.exists(task["path"]):
            path = os.path.abspath(task["path"])
            try:
                subprocess.run(["explorer", "/select,", path])
            except Exception as e:
                self.log(f"❌ 无法定位文件: {e}")
        else:
            self.log("⚠ 文件不存在或任务未完成")

    def _all_tasks_done(self):
        for d in self.task_store.values():
            s = d.get("status", "")
            if s in ("Waiting", "") or "Running" in s:
                return False
        return True

    def _clear_completed_tasks(self):
        to_delete = [tid for tid, d in self.task_store.items() if d.get("status") in ["Success", "Failed", "Cancelled", "Error"]]
        if not to_delete:
            self.log("ℹ 没有已完成的任务需要清理")
            return
        for tid in to_delete:
            self._delete_task(tid)
        self.log(f"🧹 已清除 {len(to_delete)} 个已完成任务")

    def _clear_failed_tasks(self):
        to_delete = [tid for tid, d in self.task_store.items() if d.get("status") in ["Failed", "Error"]]
        if not to_delete:
            self.log("ℹ 没有报错任务需要清理")
            return
        for tid in to_delete:
            self._delete_task(tid)
        self.log(f"🧹 已清除 {len(to_delete)} 个报错任务")

    # --- Preview ---
    def _preview_wheel_event(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.15
        else:
            factor = 1 / 1.15
        new_zoom = self._zoom_level * factor
        if 0.1 <= new_zoom <= 20.0:
            self._zoom_level = new_zoom
            self.preview_view.scale(factor, factor)

    def _show_preview(self, path):
        self.current_preview_path = path
        if not self.show_preview_cb.isChecked():
            return
        if not path or not os.path.exists(path):
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        self.meta_label.setText(
            f"{os.path.basename(path)}  ·  {pixmap.width()} × {pixmap.height()}"
        )
        self.preview_scene.clear()
        self._preview_placeholder = None
        self._preview_pixmap_item = self.preview_scene.addPixmap(pixmap)
        self._preview_pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.preview_scene.setSceneRect(QRectF(pixmap.rect()))
        self.preview_view.resetTransform()
        self._zoom_level = 1.0
        self.preview_view.fitInView(
            self.preview_scene.sceneRect(), Qt.KeepAspectRatio
        )

    def _toggle_preview_visibility(self, state):
        is_on = state != 0
        if "settings" not in self.cfg_mgr.data:
            self.cfg_mgr.data["settings"] = {}
        self.cfg_mgr.data["settings"]["show_preview"] = is_on
        self.cfg_mgr.save_data()
        if is_on:
            if self.current_preview_path:
                self._show_preview(self.current_preview_path)
            else:
                self.preview_scene.clear()
                self._preview_placeholder = self.preview_scene.addText(
                    "No Image", QFont("Segoe UI", 14)
                )
                self._preview_placeholder.setDefaultTextColor(QColor("#999999"))
        else:
            self.preview_scene.clear()
            self._preview_placeholder = self.preview_scene.addText(
                "Preview Hidden", QFont("Segoe UI", 14)
            )
            self._preview_placeholder.setDefaultTextColor(QColor("#999999"))

    def _open_preview(self, path=None):
        path = path or self.current_preview_path
        if not path or not os.path.exists(path):
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return

        self.current_preview_path = path
        is_reference = path in self.selected_image_paths
        is_mask_target = is_reference and bool(self.selected_image_paths) and path == self.selected_image_paths[0]

        dialog = QDialog(self)
        dialog.setObjectName("LightboxDialog")
        dialog.setWindowTitle(os.path.basename(path))
        dialog.setModal(True)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        dialog.resize(min(1120, max(720, screen.width() - 180)), min(860, max(560, screen.height() - 160)))

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(14, 14, 14, 12)
        dialog_layout.setSpacing(10)
        view = QGraphicsView()
        view.setObjectName("LightboxView")
        view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        view.setDragMode(QGraphicsView.ScrollHandDrag)
        scene = QGraphicsScene(view)
        scene.addPixmap(pixmap)
        scene.setSceneRect(QRectF(pixmap.rect()))
        view.setScene(scene)
        dialog_layout.addWidget(view, 1)

        footer = QHBoxLayout()
        footer_label = QLabel(f"{pixmap.width()} × {pixmap.height()}  ·  {os.path.basename(path)}")
        footer_label.setObjectName("LightboxMeta")
        footer.addWidget(footer_label, 1)

        if is_reference:
            replace_btn = QPushButton("替换图片")
            replace_btn.setObjectName("GhostButton")
            replace_btn.clicked.connect(lambda: (self._replace_reference_image(path), dialog.accept()))
            footer.addWidget(replace_btn)

            edit_btn = QPushButton("编辑遮罩")
            edit_btn.setObjectName("PrimarySmallButton")
            edit_btn.setEnabled(is_mask_target)
            edit_btn.setToolTip("遮罩只能以第一张参考图为主图")
            edit_btn.clicked.connect(lambda: (self._edit_mask(), dialog.accept()))
            footer.addWidget(edit_btn)

            remove_btn = QPushButton("移除")
            remove_btn.setObjectName("DangerLinkButton")
            remove_btn.clicked.connect(lambda: (self._remove_ref_image(path), dialog.accept()))
            footer.addWidget(remove_btn)
        else:
            use_ref_btn = QPushButton("用作参考图")
            use_ref_btn.setObjectName("GhostButton")
            use_ref_btn.clicked.connect(lambda: (self._send_preview_to_ref(), dialog.accept()))
            footer.addWidget(use_ref_btn)
            metadata_btn = QPushButton("查看参数")
            metadata_btn.setObjectName("GhostButton")
            metadata_btn.clicked.connect(lambda: self._show_metadata_dialog(path))
            footer.addWidget(metadata_btn)
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("PrimarySmallButton")
        close_btn.clicked.connect(dialog.accept)
        footer.addWidget(close_btn)
        dialog_layout.addLayout(footer)

        def fit_view(*_args):
            view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

        dialog.resizeEvent = fit_view
        QTimer.singleShot(0, fit_view)
        dialog.exec()

    def _load_history(self):
        self._clear_gallery()
        output_dir = self.output_dir_entry.text().strip()
        limit = self.current_settings.get("history_limit", 60)
        paths = ImageUtils.list_image_files(output_dir, limit)
        for path in reversed(paths):
            self._add_to_gallery(path, None)
        if paths:
            self._show_preview(paths[0])

    def _clear_gallery(self):
        for widget in list(self.gallery_widgets.values()):
            widget.deleteLater()
        self.gallery_widgets.clear()
        self.gallery_order.clear()
        self.gallery_task_ids.clear()
        self.gallery_favorites.clear()
        self._relayout_gallery()

    @staticmethod
    def _fit_thumbnail(pixmap, size):
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (scaled.width() - size) // 2)
        y = max(0, (scaled.height() - size) // 2)
        return scaled.copy(x, y, size, size)

    def _create_gallery_card(self, path, tid=None):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None

        card = QFrame(self.gallery_inner)
        card.setObjectName("GalleryCard")
        card.setFixedSize(282, 316)
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip(os.path.basename(path))
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, p=path, w=card: self._gallery_context_menu(pos, p, w)
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(5, 5, 5, 6)
        card_layout.setSpacing(4)
        image_label = QLabel(card)
        image_label.setObjectName("GalleryThumb")
        image_label.setFixedSize(272, 272)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setPixmap(self._fit_thumbnail(pixmap, 272))
        image_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        card_layout.addWidget(image_label)

        name_label = QLabel(os.path.splitext(os.path.basename(path))[0])
        name_label.setObjectName("GalleryCardName")
        name_label.setTextFormat(Qt.PlainText)
        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        card_layout.addWidget(name_label)

        def click(event, p=path):
            if event.button() == Qt.LeftButton:
                self._show_preview(p)
                self._open_preview(p)
            QFrame.mousePressEvent(card, event)

        def double_click(event, p=path):
            QFrame.mouseDoubleClickEvent(card, event)

        card.mousePressEvent = click
        card.mouseDoubleClickEvent = double_click
        return card

    def _gallery_columns(self):
        width = self.gallery_scroll.viewport().width()
        return max(1, min(3, (max(width, 294) + 12) // 294))

    def _toggle_gallery_favorites(self, _checked=False):
        self._relayout_gallery()

    def _filter_gallery(self, *_args):
        self._relayout_gallery()

    def _gallery_item_visible(self, path):
        query = self.search_entry.text().strip().lower() if hasattr(self, "search_entry") else ""
        if query:
            haystack = os.path.basename(path).lower()
            task_id = self.gallery_task_ids.get(path)
            task = self.task_store.get(task_id, {}) if task_id else {}
            haystack += " " + str(task.get("config", {}).get("prompt", "")).lower()
            if query not in haystack:
                return False

        if getattr(self, "favorite_filter_btn", None) and self.favorite_filter_btn.isChecked():
            if path not in self.gallery_favorites:
                return False

        status_filter = self.search_filter_combo.currentData() if hasattr(self, "search_filter_combo") else "all"
        if status_filter == "all":
            return True
        task_id = self.gallery_task_ids.get(path)
        status = str(self.task_store.get(task_id, {}).get("status", "Success")) if task_id else "Success"
        if status_filter == "done":
            return status in {"Success", "Completed", "Done"}
        if status_filter == "running":
            return "Running" in status or status in {"Waiting", "Queued"}
        if status_filter == "error":
            return status in {"Failed", "Error"}
        return True

    def _relayout_gallery(self):
        if not hasattr(self, "gallery_inner_layout"):
            return
        while self.gallery_inner_layout.count():
            item = self.gallery_inner_layout.takeAt(0)
            if item and item.widget() and item.widget() is not self.gallery_empty_label:
                item.widget().setParent(self.gallery_inner)

        columns = self._gallery_columns()
        for column in range(columns):
            self.gallery_inner_layout.setColumnStretch(column, 1)
        visible_paths = [path for path in self.gallery_order if self._gallery_item_visible(path)]
        if not visible_paths:
            self.gallery_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.gallery_inner.setMinimumHeight(max(260, self.gallery_scroll.viewport().height() - 28))
            self.gallery_empty_label.setVisible(True)
            if self.favorite_filter_btn.isChecked():
                self.gallery_empty_label.setText("还没有收藏图片")
            elif self.search_entry.text().strip() or self.search_filter_combo.currentData() != "all":
                self.gallery_empty_label.setText("没有找到匹配的图片")
            else:
                self.gallery_empty_label.setText("输入提示词开始生成图片")
            self.gallery_inner_layout.addWidget(
                self.gallery_empty_label, 0, 0, 1, columns, Qt.AlignCenter
            )
        else:
            self.gallery_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.gallery_inner.setMinimumHeight(0)
            self.gallery_empty_label.setVisible(False)
            for index, path in enumerate(visible_paths):
                widget = self.gallery_widgets.get(path)
                if widget:
                    row, column = divmod(index, columns)
                    self.gallery_inner_layout.addWidget(widget, row, column)

        self.gallery_count_label.setText(f"{len(visible_paths)} / {len(self.gallery_order)}")

    def _add_to_gallery(self, path, tid=None):
        if not path or not os.path.isfile(path):
            return
        if path in self.gallery_order:
            self.gallery_order.remove(path)
            existing = self.gallery_widgets.pop(path, None)
            if existing:
                existing.deleteLater()

        limit = max(1, int(self.current_settings.get("history_limit", 60)))
        while len(self.gallery_order) >= limit:
            old_path = self.gallery_order.pop()
            old_widget = self.gallery_widgets.pop(old_path, None)
            if old_widget:
                old_widget.deleteLater()

        card = self._create_gallery_card(path, tid)
        if card is None:
            return
        self.gallery_order.insert(0, path)
        self.gallery_widgets[path] = card
        if tid:
            self.gallery_task_ids[path] = tid
        self._relayout_gallery()

    def _gallery_context_menu(self, pos, path, widget):
        menu = QMenu(self)
        menu.addAction("📋 查看生成参数", lambda: self._show_metadata_dialog(path))
        menu.addAction("📎 用作参考图", lambda: self._add_images([path]))
        favorite_text = "取消收藏" if path in self.gallery_favorites else "收藏"
        menu.addAction(favorite_text, lambda: self._toggle_gallery_favorite(path))
        menu.addAction("📂 在文件夹中选中", lambda: self._reveal_file(path))
        menu.exec(widget.mapToGlobal(pos))

    def _toggle_gallery_favorite(self, path):
        if path in self.gallery_favorites:
            self.gallery_favorites.remove(path)
        else:
            self.gallery_favorites.add(path)
        self._relayout_gallery()

    def _show_metadata_dialog(self, path):
        meta = ImageUtils.read_metadata(path)
        if not meta:
            QMessageBox.information(self, "生成参数", "未找到元数据（非本工具生成的图片）")
            return
        api_type = meta.get("api_type", "gemini")
        lines = [f"模型: {meta.get('model', '?')}"]
        if api_type == "gpt":
            lines.append(f"API接口: {meta.get('api_mode', 'images')}")
            lines.append(
                f"尺寸: {meta.get('size', '?')} | 画质: {meta.get('quality', '?')} | "
                f"格式: {meta.get('output_format', 'png')} | 数量: {meta.get('n', 1)}"
            )
            lines.append(
                f"审核: {meta.get('moderation', 'auto')} | 压缩率: "
                f"{meta.get('output_compression') or 0}%"
            )
        else:
            lines.append(f"比例: {meta.get('aspect_ratio', '?')} | 尺寸: {meta.get('resolution', '?')}")
        lines.append(f"API类型: {api_type}")
        ref = meta.get("ref_images", [])
        if ref:
            lines.append(f"参考图: {', '.join(ref)}")
        prompt = meta.get("prompt", "")
        if len(prompt) > 500:
            prompt = prompt[:500] + "..."
        lines.append(f"\n--- 提示词 ---\n{prompt}")
        QMessageBox.information(self, f"生成参数 - {os.path.basename(path)}", "\n".join(lines))

    def _load_metadata_to_ui(self, path):
        meta = ImageUtils.read_metadata(path)
        if not meta:
            self.log("⚠ 未找到元数据")
            return
        self._apply_config_to_ui(meta)
        self.log(f"📋 已从 {os.path.basename(path)} 读取生成参数")

    def _reveal_file(self, path):
        if os.path.exists(path):
            try:
                subprocess.run(["explorer", "/select,", os.path.abspath(path)])
            except Exception as e:
                self.log(f"❌ 无法定位文件: {e}")

    def _send_preview_to_ref(self):
        if self.current_preview_path and os.path.exists(self.current_preview_path):
            self._add_images([self.current_preview_path])
            self.log("📎 已添加预览图为参考图")
        else:
            self.log("⚠ 当前没有预览图")

    # --- Reference Images ---
    def _select_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择参考图片", "",
                                                 "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if files:
            self._add_images(files)

    def _add_images(self, paths):
        for p in paths:
            if p not in self.selected_image_paths and os.path.isfile(p):
                if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                    self.selected_image_paths.append(p)
        self.ref_count_label.setText(f"{len(self.selected_image_paths)} 张")
        self._refresh_ref_gallery()

    def _clear_images(self):
        self.selected_image_paths = []
        self.ref_count_label.setText("0 张")
        self._clear_mask()
        self._refresh_ref_gallery()

    def _edit_mask(self):
        if not self.selected_image_paths:
            QMessageBox.warning(self, "提示", "请先添加一张参考图")
            return

        source_path = self.selected_image_paths[0]
        dialog = MaskEditorDialog(source_path, self.selected_mask_path, self)
        if dialog.exec() != QDialog.Accepted:
            return

        output_dir = self.output_dir_entry.text().strip() or "images"
        mask_dir = os.path.join(os.path.abspath(output_dir), "masks")
        os.makedirs(mask_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(source_path))[0]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(mask_dir, f"{stem}_mask_{stamp}.png")
        if not dialog.get_mask().save(path, "PNG"):
            QMessageBox.warning(self, "提示", "遮罩保存失败")
            return
        self.selected_mask_path = path
        self.mask_label.setText(os.path.basename(path))
        self.mask_label.setToolTip(path)
        self.log(f"🎭 已保存遮罩: {os.path.basename(path)}")
        self._refresh_ref_gallery()

    def _clear_mask(self):
        self.selected_mask_path = None
        if hasattr(self, "mask_label"):
            self.mask_label.setText("未选择遮罩")
            self.mask_label.setToolTip("遮罩会作为 mask 字段上传，并要求至少有一张参考图")

    def _replace_reference_image(self, old_path):
        if old_path not in self.selected_image_paths:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "替换参考图片", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not files:
            return
        replacement = files[0]
        index = self.selected_image_paths.index(old_path)
        if replacement in self.selected_image_paths:
            QMessageBox.information(self, "提示", "这张图片已经在参考图列表中")
            return
        self.selected_image_paths[index] = replacement
        if index == 0 and self.selected_mask_path:
            self._clear_mask()
        self.ref_count_label.setText(f"{len(self.selected_image_paths)} 张")
        self._refresh_ref_gallery()
        self.log(f"📎 已替换参考图: {os.path.basename(replacement)}")

    def _refresh_ref_gallery(self):
        while self.ref_inner_layout.count():
            item = self.ref_inner_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self.ref_scroll.setVisible(bool(self.selected_image_paths))
        self.clear_images_btn.setVisible(bool(self.selected_image_paths))

        for fpath in self.selected_image_paths:
            pixmap = QPixmap(fpath)
            if pixmap.isNull():
                continue
            thumb = self._fit_thumbnail(pixmap, 54)
            lbl = QLabel()
            lbl.setObjectName("ReferenceThumb")
            lbl.setFixedSize(58, 58)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setPixmap(thumb)
            lbl.setToolTip(os.path.basename(fpath))
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.setProperty("hasMask", fpath == self.selected_image_paths[0] and bool(self.selected_mask_path))
            lbl.mousePressEvent = lambda event, p=fpath: self._open_reference_from_thumb(event, p)
            lbl.setContextMenuPolicy(Qt.CustomContextMenu)
            lbl.customContextMenuRequested.connect(
                lambda pos, p=fpath, w=lbl: self._ref_context_menu(pos, p, w)
            )
            self.ref_inner_layout.addWidget(lbl)
        self.ref_inner_layout.addStretch()

    def _open_reference_from_thumb(self, event, fpath):
        if event.button() == Qt.LeftButton:
            self._show_preview(fpath)
            self._open_preview(fpath)

    def _ref_context_menu(self, pos, fpath, widget):
        menu = QMenu(self)
        menu.addAction("📋 读取生成参数", lambda: self._load_metadata_to_ui(fpath))
        menu.addAction("📋 查看生成参数", lambda: self._show_metadata_dialog(fpath))
        menu.addSeparator()
        menu.addAction("❌ 移除此图", lambda: self._remove_ref_image(fpath))
        menu.exec(widget.mapToGlobal(pos))

    def _remove_ref_image(self, fpath):
        if fpath in self.selected_image_paths:
            was_mask_source = fpath == self.selected_image_paths[0]
            self.selected_image_paths.remove(fpath)
            if was_mask_source and self.selected_mask_path:
                self._clear_mask()
            self.ref_count_label.setText(f"{len(self.selected_image_paths)} 张")
            self._refresh_ref_gallery()
            self.log(f"🗑 已移除参考图: {os.path.basename(fpath)}")

    # --- Drag & Drop ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self._add_images(paths)

    # --- Clipboard Paste ---
    def _paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            image = clipboard.image()
            if not image.isNull():
                temp_dir = os.path.join(self.current_settings.get("output_dir", "images"), "temp_paste")
                os.makedirs(temp_dir, exist_ok=True)
                fname = f"paste_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                temp_path = os.path.join(temp_dir, fname)
                image.save(temp_path, "PNG")
                self._add_images([temp_path])
                self.log("📋 已粘贴剪贴板图片")
        elif mime.hasUrls():
            paths = [url.toLocalFile() for url in mime.urls()
                     if url.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
            if paths:
                self._add_images(paths)
                self.log(f"📋 已粘贴 {len(paths)} 个文件")

    # --- Utility ---
    def _cleanup_memory(self):
        self.current_preview_path = None
        self.preview_scene.clear()
        self._preview_pixmap_item = None
        self._preview_placeholder = self.preview_scene.addText(
            "No Image", QFont("Segoe UI", 14)
        )
        self._preview_placeholder.setDefaultTextColor(QColor("#999999"))
        self._clear_gallery()

        to_delete = [tid for tid, d in self.task_store.items()
                     if "Running" not in d.get("status", "") and "Waiting" not in d.get("status", "")]
        for tid in to_delete:
            self._delete_task(tid)
        gc.collect()
        self.log("🧹 内存清理完毕")

    def _open_output_dir(self):
        d = self.output_dir_entry.text().strip()
        if not os.path.exists(d):
            os.makedirs(d)
        try:
            os.startfile(os.path.abspath(d))
        except Exception:
            pass

    def _choose_output_dir(self):
        current = self.output_dir_entry.text().strip() or os.getcwd()
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", os.path.abspath(current))
        if not path:
            return
        self.output_dir_entry.setText(path)
        self.current_settings["output_dir"] = path
        self.cfg_mgr.save_data()
        self._clear_gallery()
        self._load_history()
        self.log(f"📂 输出目录已切换: {path}")

    def _update_char_count(self):
        text = self.prompt_text.toPlainText()
        self.lbl_char_count.setText(f"{len(text)} 字")

    def _change_window_size(self, idx):
        if idx < 0:
            return
        w, h, _ = self.resolution_options[idx]
        self.resize(w, h)
        if "settings" in self.cfg_mgr.data:
            self.cfg_mgr.data["settings"]["window_size_idx"] = idx
            self.cfg_mgr.save_data()

    def _change_theme(self, theme_name):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(get_qss(theme_name))
        if "settings" not in self.cfg_mgr.data:
            self.cfg_mgr.data["settings"] = {}
        self.cfg_mgr.data["settings"]["theme"] = theme_name
        self.cfg_mgr.save_data()

    def _on_worker_count_changed(self, value):
        self.task_manager.set_max_workers(value)
        if "settings" not in self.cfg_mgr.data:
            self.cfg_mgr.data["settings"] = {}
        self.cfg_mgr.data["settings"]["max_workers"] = value
        self.cfg_mgr.save_data()
        self.log(f"⚙ 最大并发数: {value}")

    def _on_batch_count_changed(self, value):
        if "settings" not in self.cfg_mgr.data:
            self.cfg_mgr.data["settings"] = {}
        self.cfg_mgr.data["settings"]["batch_count"] = value
        self.cfg_mgr.save_data()

    def _on_sound_toggle(self, state):
        if "settings" not in self.cfg_mgr.data:
            self.cfg_mgr.data["settings"] = {}
        self.cfg_mgr.data["settings"]["sound_notify"] = (state != 0)
        self.cfg_mgr.save_data()

    # --- Profile Ops ---
    def _refresh_profile_ui(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for p in self.cfg_mgr.get_profiles():
            self.profile_combo.addItem(p["name"])
        self.profile_combo.setCurrentIndex(self.cfg_mgr.data.get("current_profile_idx", 0))
        self.profile_combo.blockSignals(False)
        self._fill_profile_inputs(self.cfg_mgr.get_current_profile())

    def _fill_profile_inputs(self, p):
        self.api_url_entry.setText(p.get("api_url", ""))
        self.api_key_entry.setText(p.get("api_key", ""))
        self.model_entry.setText(p.get("model", ""))
        api_type = p.get("api_type", "gemini")
        self.api_type_combo.setCurrentIndex(1 if api_type == "gpt" else 0)
        self.current_api_type = api_type
        api_mode = p.get("api_mode", "images")
        mode_index = self.api_mode_combo.findData(api_mode)
        self.api_mode_combo.setCurrentIndex(max(0, mode_index))
        self._refresh_param_panel()

    def _on_profile_selected(self, idx):
        if idx < 0:
            return
        self.cfg_mgr.set_current_profile_idx(idx)
        profiles = self.cfg_mgr.get_profiles()
        if 0 <= idx < len(profiles):
            self._fill_profile_inputs(profiles[idx])

    def _on_api_type_changed(self, idx):
        self.current_api_type = "gpt" if idx == 1 else "gemini"
        self._refresh_param_panel()

    def _refresh_param_panel(self):
        self.ratio_combo.blockSignals(True)
        self.res_combo.blockSignals(True)
        self.ratio_combo.clear()
        self.res_combo.clear()

        if self.current_api_type == "gpt":
            self.param1_label.setText("图片尺寸:")
            self.ratio_combo.addItems(self.gpt_size_options)
            self.ratio_combo.setCurrentIndex(min(self.current_settings.get("gpt_size_idx", 0), len(self.gpt_size_options) - 1))
            self.param2_label.setText("图片画质:")
            self.res_combo.addItems(self.gpt_quality_options)
            self.res_combo.setCurrentIndex(min(self.current_settings.get("gpt_quality_idx", 0), len(self.gpt_quality_options) - 1))
            self.output_format_chip.setVisible(True)
            self.moderation_chip.setVisible(True)
            self.compression_chip.setVisible(True)
            self.api_mode_combo.setVisible(True)
            self.api_mode_label.setVisible(True)
            self._refresh_compression_state()
        else:
            self.param1_label.setText("图像比例:")
            self.ratio_combo.addItems(list(self.ratio_map.keys()))
            self.ratio_combo.setCurrentIndex(min(self.current_settings.get("aspect_ratio_idx", 1), len(self.ratio_map) - 1))
            self.param2_label.setText("图像尺寸:")
            self.res_combo.addItems(["1K", "2K", "4K"])
            self.res_combo.setCurrentIndex(min(self.current_settings.get("resolution_idx", 2), 2))
            self.output_format_chip.setVisible(False)
            self.moderation_chip.setVisible(False)
            self.compression_chip.setVisible(False)
            self.api_mode_combo.setVisible(False)
            self.api_mode_label.setVisible(False)

        self.ratio_combo.blockSignals(False)
        self.res_combo.blockSignals(False)

    def _refresh_compression_state(self):
        if not hasattr(self, "compression_spin"):
            return
        enabled = self.current_api_type == "gpt" and self.output_format_combo.currentText() != "PNG"
        self.compression_spin.setEnabled(enabled)
        self.compression_label.setEnabled(enabled)

    def _save_profile_changes(self):
        api_type = "gpt" if self.api_type_combo.currentIndex() == 1 else "gemini"
        self.cfg_mgr.update_profile(self.profile_combo.currentIndex(), api_type,
                                    self.api_url_entry.text(), self.api_key_entry.text(),
                                    self.model_entry.text(),
                                    self.api_mode_combo.currentData() or "images")
        self.log("✅ Profile Updated")

    def _create_new_profile(self):
        name, ok = QInputDialog.getText(self, "新建配置", "配置名称:")
        if ok and name:
            api_type = "gpt" if self.api_type_combo.currentIndex() == 1 else "gemini"
            self.cfg_mgr.add_profile(name, api_type, self.api_url_entry.text(),
                                     self.api_key_entry.text(), self.model_entry.text(),
                                     self.api_mode_combo.currentData() or "images")
            self._refresh_profile_ui()

    def _delete_current_profile(self):
        if self.cfg_mgr.delete_profile(self.profile_combo.currentIndex()):
            self._refresh_profile_ui()

    # --- Prompt Ops ---
    def _refresh_prompt_ui(self):
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("--- 选择预设 ---")
        for p in self.cfg_mgr.get_prompts():
            self.prompt_combo.addItem(p["name"])
        self.prompt_combo.blockSignals(False)

    def _on_prompt_selected(self, idx):
        if idx <= 0:
            return
        prompts = self.cfg_mgr.get_prompts()
        if 0 <= idx - 1 < len(prompts):
            self.prompt_text.setPlainText(prompts[idx - 1]["content"])

    def _update_current_prompt(self):
        idx = self.prompt_combo.currentIndex() - 1
        if idx >= 0:
            self.cfg_mgr.update_prompt(idx, self.prompt_text.toPlainText().strip())
            self.log("✅ 提示词已更新")

    def _save_as_new_prompt(self):
        name, ok = QInputDialog.getText(self, "保存提示词", "名称:")
        if ok and name:
            self.cfg_mgr.add_prompt(name, self.prompt_text.toPlainText().strip())
            self._refresh_prompt_ui()

    def _delete_current_prompt(self):
        idx = self.prompt_combo.currentIndex() - 1
        if idx >= 0:
            self.cfg_mgr.delete_prompt(idx)
            self._refresh_prompt_ui()

    # --- Window Events ---
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "gallery_inner_layout"):
            self._relayout_gallery()
        if (self.current_preview_path and self.show_preview_cb.isChecked()
                and self._preview_pixmap_item and self.preview_view.isVisible()):
            self.preview_view.fitInView(
                self.preview_scene.sceneRect(), Qt.KeepAspectRatio
            )
            self._zoom_level = 1.0

    def closeEvent(self, event):
        self.task_manager.active = False
        event.accept()
