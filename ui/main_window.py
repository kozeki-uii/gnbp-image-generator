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
    QMessageBox, QMenu, QAbstractItemView, QHeaderView,
    QSpinBox, QGridLayout, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsTextItem
)
from PySide6.QtCore import Qt, QTimer, QMimeData, QRectF
from PySide6.QtGui import QPixmap, QImage, QColor, QGuiApplication, QShortcut, QKeySequence, QAction, QFont, QPainter

from app_info import APP_TITLE
from config.config_mgr import ConfigManager, GenConfig, CONFIG_FILE
from core.task_queue import TaskManager
from core.utils import ImageUtils
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
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)

        self.splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(self.splitter)

        left_widget = QWidget()
        self.left_layout = QVBoxLayout(left_widget)
        self.left_layout.setContentsMargins(0, 0, 4, 0)
        self.left_layout.setSpacing(8)
        self.splitter.addWidget(left_widget)

        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(4, 0, 0, 0)
        self.right_layout.setSpacing(8)
        self.splitter.addWidget(right_widget)

        self.splitter.setSizes([650, 550])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self._build_api_section()
        self._build_prompt_section()
        self._build_settings_section()
        self._build_action_section()
        self._build_notebook_section()
        self._build_preview_section()

    # --- API Section ---
    def _build_api_section(self):
        header = QHBoxLayout()

        self.btn_api_toggle = QPushButton("⚙ 展开配置")
        self.btn_api_toggle.setCheckable(True)
        self.btn_api_toggle.clicked.connect(self._toggle_api_panel)
        header.addWidget(self.btn_api_toggle)

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(120)
        self.profile_combo.setMaximumWidth(200)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        header.addWidget(self.profile_combo)

        header.addStretch()

        self.size_combo = QComboBox()
        self.size_combo.addItems([opt[2] for opt in self.resolution_options])
        saved_idx = self.current_settings.get("window_size_idx", 1)
        self.size_combo.setCurrentIndex(min(saved_idx, len(self.resolution_options) - 1))
        self.size_combo.currentIndexChanged.connect(self._change_window_size)
        header.addWidget(self.size_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_NAMES)
        saved_theme = self.current_settings.get("theme", "米黄")
        if saved_theme in THEME_NAMES:
            self.theme_combo.setCurrentText(saved_theme)
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        header.addWidget(self.theme_combo)

        self.left_layout.addLayout(header)

        self.api_detail_group = QGroupBox("参数详情")
        form = QFormLayout(self.api_detail_group)
        form.setSpacing(6)

        self.api_url_entry = QLineEdit()
        form.addRow("API地址:", self.api_url_entry)

        key_row = QHBoxLayout()
        self.api_key_entry = QLineEdit()
        self.api_key_entry.setEchoMode(QLineEdit.Password)
        key_row.addWidget(self.api_key_entry)
        self.btn_eye = QPushButton("👁")
        self.btn_eye.setProperty("cssClass", "link")
        self.btn_eye.setFixedWidth(36)
        self.btn_eye.clicked.connect(self._toggle_key_view)
        key_row.addWidget(self.btn_eye)
        form.addRow("API密钥:", key_row)

        self.model_entry = QLineEdit()
        form.addRow("模型:", self.model_entry)

        self.api_type_combo = QComboBox()
        self.api_type_combo.addItems(["Gemini", "GPT"])
        self.api_type_combo.currentIndexChanged.connect(self._on_api_type_changed)
        form.addRow("API类型:", self.api_type_combo)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("+ 新建")
        btn_new.clicked.connect(self._create_new_profile)
        btn_row.addWidget(btn_new)
        btn_del = QPushButton("🗑 删除")
        btn_del.setProperty("cssClass", "danger")
        btn_del.clicked.connect(self._delete_current_profile)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_save = QPushButton("💾 保存修改")
        btn_save.clicked.connect(self._save_profile_changes)
        btn_row.addWidget(btn_save)
        form.addRow(btn_row)

        self.api_detail_group.setVisible(False)
        self.left_layout.addWidget(self.api_detail_group)

    # --- Prompt Section ---
    def _build_prompt_section(self):
        group = QGroupBox("📚 提示词 (Prompt)")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.prompt_combo = QComboBox()
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_selected)
        top_row.addWidget(self.prompt_combo, 1)

        for text, slot in [("💾", self._update_current_prompt), ("🆕", self._save_as_new_prompt), ("🗑", self._delete_current_prompt)]:
            btn = QPushButton(text)
            btn.setProperty("cssClass", "link")
            btn.setFixedWidth(36)
            btn.clicked.connect(slot)
            top_row.addWidget(btn)

        self.lbl_char_count = QLabel("Len: 0")
        self.lbl_char_count.setStyleSheet("font-family: Consolas; font-size: 9pt; color: #888888;")
        top_row.addWidget(self.lbl_char_count)

        layout.addLayout(top_row)

        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("在此输入提示词...")
        self.prompt_text.textChanged.connect(self._update_char_count)
        layout.addWidget(self.prompt_text)

        self.left_layout.addWidget(group, 1)

    # --- Settings Section ---
    def _build_settings_section(self):
        row = QHBoxLayout()

        param_group = QGroupBox("⚙ 图像参数")
        grid = QGridLayout(param_group)
        grid.setSpacing(4)

        self.param1_label = QLabel("图像比例:")
        grid.addWidget(self.param1_label, 0, 0)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(list(self.ratio_map.keys()))
        self.ratio_combo.setCurrentIndex(min(self.current_settings.get("aspect_ratio_idx", 1), len(self.ratio_map) - 1))
        grid.addWidget(self.ratio_combo, 0, 1)

        grid.addWidget(QLabel("生成数量:"), 0, 2)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 99)
        self.batch_spin.setValue(self.current_settings.get("batch_count", 1))
        self.batch_spin.valueChanged.connect(self._on_batch_count_changed)
        grid.addWidget(self.batch_spin, 0, 3)

        self.param2_label = QLabel("图像尺寸:")
        grid.addWidget(self.param2_label, 1, 0)
        self.res_combo = QComboBox()
        self.res_combo.addItems(["1K", "2K", "4K"])
        self.res_combo.setCurrentIndex(min(self.current_settings.get("resolution_idx", 2), 2))
        grid.addWidget(self.res_combo, 1, 1)

        grid.addWidget(QLabel("最大并发:"), 1, 2)
        self.worker_spin = QSpinBox()
        self.worker_spin.setRange(1, 8)
        self.worker_spin.setValue(self.current_settings.get("max_workers", 1))
        self.worker_spin.valueChanged.connect(self._on_worker_count_changed)
        grid.addWidget(self.worker_spin, 1, 3)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        cb_row = QHBoxLayout()
        cb_row.setSpacing(24)
        self.show_preview_cb = QCheckBox("实时预览")
        self.show_preview_cb.setChecked(self.current_settings.get("show_preview", True))
        self.show_preview_cb.stateChanged.connect(self._toggle_preview_visibility)
        cb_row.addWidget(self.show_preview_cb)

        self.sound_cb = QCheckBox("完成提示音")
        self.sound_cb.setChecked(self.current_settings.get("sound_notify", True))
        self.sound_cb.stateChanged.connect(self._on_sound_toggle)
        cb_row.addWidget(self.sound_cb)

        cb_row.addStretch()
        grid.addLayout(cb_row, 2, 0, 1, 4)

        row.addWidget(param_group, 2)

        ref_group = QGroupBox("🖼 参考图像")
        ref_layout = QVBoxLayout(ref_group)
        ref_layout.setSpacing(4)

        ref_btns = QHBoxLayout()
        btn_open = QPushButton("📂 打开图片")
        btn_open.clicked.connect(self._select_images)
        ref_btns.addWidget(btn_open)
        btn_clear = QPushButton("❌ 清空图片")
        btn_clear.setProperty("cssClass", "danger")
        btn_clear.clicked.connect(self._clear_images)
        ref_btns.addWidget(btn_clear)
        self.ref_count_label = QLabel("0 files")
        self.ref_count_label.setProperty("cssClass", "ref-count")
        ref_btns.addWidget(self.ref_count_label)
        ref_layout.addLayout(ref_btns)

        self.ref_scroll = QScrollArea()
        self.ref_scroll.setWidgetResizable(True)
        self.ref_scroll.setMinimumHeight(80)
        self.ref_scroll.setMaximumHeight(120)
        self.ref_inner = QWidget()
        self.ref_inner_layout = QHBoxLayout(self.ref_inner)
        self.ref_inner_layout.setContentsMargins(4, 4, 4, 4)
        self.ref_inner_layout.setSpacing(6)
        self.ref_inner_layout.addStretch()
        self.ref_scroll.setWidget(self.ref_inner)
        ref_layout.addWidget(self.ref_scroll)

        row.addWidget(ref_group, 3)
        self.left_layout.addLayout(row)

    # --- Action Section ---
    def _build_action_section(self):
        self.gen_btn = QPushButton("✨ 加入任务队列 (Ctrl+Enter)")
        self.gen_btn.setProperty("cssClass", "success")
        self.gen_btn.clicked.connect(self.on_enqueue_task)
        self.left_layout.addWidget(self.gen_btn)

        util_row = QHBoxLayout()
        for text, slot in [("📂 打开输出目录", self._open_output_dir),
                           ("🧹 清理内存占用", self._cleanup_memory),
                           ("🧹 清除报错任务", self._clear_failed_tasks)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            util_row.addWidget(btn)
        self.left_layout.addLayout(util_row)

    # --- Notebook (Task List + Log) ---
    def _build_notebook_section(self):
        self.tab_widget = QTabWidget()

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
        self.task_table.verticalHeader().setDefaultSectionSize(36)
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
        self.tab_widget.addTab(q_tab, "⏳ 任务列表")

        # Tab 2: Log
        l_tab = QWidget()
        l_layout = QVBoxLayout(l_tab)
        l_layout.setContentsMargins(0, 4, 0, 0)

        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()
        btn_clear_log = QPushButton("🗑 清除日志")
        btn_clear_log.setProperty("cssClass", "link")
        btn_clear_log.clicked.connect(lambda: self.log_text.clear())
        log_toolbar.addWidget(btn_clear_log)
        l_layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        l_layout.addWidget(self.log_text)
        self.tab_widget.addTab(l_tab, "📟 任务日志")

        self.left_layout.addWidget(self.tab_widget, 1)

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

        self._preview_placeholder = self.preview_scene.addText(
            "No Image", QFont("Segoe UI", 14)
        )
        self._preview_placeholder.setDefaultTextColor(QColor("#999999"))
        self._preview_pixmap_item = None
        self._zoom_level = 1.0

        self.right_layout.addWidget(self.preview_view, 3)

        meta_row = QHBoxLayout()
        self.meta_label = QLabel("Ready")
        self.meta_label.setProperty("cssClass", "meta")
        meta_row.addWidget(self.meta_label, 1)
        btn_ref = QPushButton("📎 用作参考图")
        btn_ref.clicked.connect(self._send_preview_to_ref)
        meta_row.addWidget(btn_ref)
        self.right_layout.addLayout(meta_row)

        gallery_group = QGroupBox("🎞 历史记录")
        gallery_layout = QVBoxLayout(gallery_group)
        gallery_layout.setContentsMargins(4, 16, 4, 4)
        gallery_layout.setSpacing(0)

        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setFixedHeight(96)
        self.gallery_inner = QWidget()
        self.gallery_inner_layout = QHBoxLayout(self.gallery_inner)
        self.gallery_inner_layout.setContentsMargins(4, 4, 4, 4)
        self.gallery_inner_layout.setSpacing(6)
        self.gallery_inner_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.gallery_scroll.setWidget(self.gallery_inner)
        gallery_layout.addWidget(self.gallery_scroll)

        self.right_layout.addWidget(gallery_group)

    # ========== Logic ==========

    def _toggle_api_panel(self, checked):
        self.api_detail_group.setVisible(checked)
        self.btn_api_toggle.setText("🔽 收起配置" if checked else "⚙ 展开配置")

    def _toggle_key_view(self):
        if self.api_key_entry.echoMode() == QLineEdit.Password:
            self.api_key_entry.setEchoMode(QLineEdit.Normal)
            self.btn_eye.setText("🔒")
        else:
            self.api_key_entry.setEchoMode(QLineEdit.Password)
            self.btn_eye.setText("👁")

    def log(self, msg):
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{ts} {msg}")

    # --- Task Queue ---
    def on_enqueue_task(self):
        prompt = self.prompt_text.toPlainText().strip()
        key = self.api_key_entry.text().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "Prompt 不能为空")
            return
        if not key:
            QMessageBox.warning(self, "提示", "API Key 不能为空")
            return

        out_dir = self.current_settings.get("output_dir", "images")
        batch_count = self.batch_spin.value()

        if self.current_api_type == "gpt":
            self.cfg_mgr.update_settings(
                self.current_settings.get("aspect_ratio_idx", 1),
                self.current_settings.get("resolution_idx", 2),
                out_dir,
                gpt_size_idx=self.ratio_combo.currentIndex(),
                gpt_quality_idx=self.res_combo.currentIndex()
            )
            size_text = self.ratio_combo.currentText()
            quality_text = self.res_combo.currentText()
        else:
            self.cfg_mgr.update_settings(
                self.ratio_combo.currentIndex(), self.res_combo.currentIndex(), out_dir
            )
            ratio_text = self.ratio_combo.currentText()

        for _ in range(batch_count):
            if self.current_api_type == "gpt":
                cfg = GenConfig(
                    api_url=self.api_url_entry.text().strip(),
                    api_key=key, model=self.model_entry.text().strip(),
                    prompt=prompt, aspect_ratio="", resolution="",
                    output_dir=out_dir, api_type="gpt",
                    ref_images=copy.copy(self.selected_image_paths),
                    size=self.gpt_size_map.get(size_text, "auto"),
                    quality=self.gpt_quality_map.get(quality_text, "auto")
                )
            else:
                cfg = GenConfig(
                    api_url=self.api_url_entry.text().strip(),
                    api_key=key, model=self.model_entry.text().strip(),
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

        btn_copy = QPushButton("复制")
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

                if data.get("path"):
                    self._show_preview(data["path"])
                    self._add_to_gallery(data["path"], tid)

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
        if tid in self.gallery_widgets:
            self.gallery_widgets[tid].deleteLater()
            del self.gallery_widgets[tid]
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
                self.meta_label.setText(f"Model: {cfg.get('model')} | Size: {cfg.get('size')} | Quality: {cfg.get('quality')}")
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
        cfg = task["config"]
        self.prompt_text.setPlainText(cfg["prompt"])
        self.model_entry.setText(cfg["model"])
        for k, v in self.ratio_map.items():
            if v == cfg.get("aspect_ratio"):
                self.ratio_combo.setCurrentText(k)
                break
        self.log("📋 参数已载入")

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

    def _open_preview(self):
        if self.current_preview_path and os.path.exists(self.current_preview_path):
            try:
                os.startfile(self.current_preview_path)
            except Exception:
                pass

    def _add_to_gallery(self, path, tid):
        count = self.gallery_inner_layout.count()
        if count > 9:
            item = self.gallery_inner_layout.takeAt(0)
            if item and item.widget():
                w = item.widget()
                for k, v in list(self.gallery_widgets.items()):
                    if v is w:
                        del self.gallery_widgets[k]
                        break
                w.deleteLater()

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        thumb = pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl = QLabel()
        lbl.setFixedSize(76, 76)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setPixmap(thumb)
        lbl.setCursor(Qt.PointingHandCursor)
        lbl.setToolTip(os.path.basename(path))
        lbl.setStyleSheet("border: 1px solid #D4C9B8; border-radius: 4px; background: #FFFFFF;")
        lbl.setContextMenuPolicy(Qt.CustomContextMenu)
        lbl.customContextMenuRequested.connect(lambda pos, p=path, w=lbl: self._gallery_context_menu(pos, p, w))
        lbl.mousePressEvent = lambda e, p=path: self._show_preview(p) if e.button() == Qt.LeftButton else None
        self.gallery_inner_layout.addWidget(lbl)
        self.gallery_widgets[tid] = lbl

    def _gallery_context_menu(self, pos, path, widget):
        menu = QMenu(self)
        menu.addAction("📋 查看生成参数", lambda: self._show_metadata_dialog(path))
        menu.addAction("📎 用作参考图", lambda: self._add_images([path]))
        menu.addAction("📂 在文件夹中选中", lambda: self._reveal_file(path))
        menu.exec(widget.mapToGlobal(pos))

    def _show_metadata_dialog(self, path):
        meta = ImageUtils.read_metadata(path)
        if not meta:
            QMessageBox.information(self, "生成参数", "未找到元数据（非本工具生成的图片）")
            return
        api_type = meta.get("api_type", "gemini")
        lines = [f"模型: {meta.get('model', '?')}"]
        if api_type == "gpt":
            lines.append(f"尺寸: {meta.get('size', '?')} | 画质: {meta.get('quality', '?')}")
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
        if meta.get("prompt"):
            self.prompt_text.setPlainText(meta["prompt"])
        if meta.get("model"):
            self.model_entry.setText(meta["model"])
        api_type = meta.get("api_type", "gemini")
        if api_type == "gpt":
            self.api_type_combo.setCurrentIndex(1)
            size = meta.get("size", "auto")
            for k, v in self.gpt_size_map.items():
                if v == size:
                    self.ratio_combo.setCurrentText(k)
                    break
            quality = meta.get("quality", "auto")
            for k, v in self.gpt_quality_map.items():
                if v == quality:
                    self.res_combo.setCurrentText(k)
                    break
        else:
            self.api_type_combo.setCurrentIndex(0)
            ratio = meta.get("aspect_ratio", "")
            for k, v in self.ratio_map.items():
                if v == ratio:
                    self.ratio_combo.setCurrentText(k)
                    break
            res = meta.get("resolution", "")
            idx = ["1K", "2K", "4K"].index(res) if res in ["1K", "2K", "4K"] else -1
            if idx >= 0:
                self.res_combo.setCurrentIndex(idx)
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
        self.ref_count_label.setText(f"{len(self.selected_image_paths)} files")
        self._refresh_ref_gallery()

    def _clear_images(self):
        self.selected_image_paths = []
        self.ref_count_label.setText("0 files")
        self._refresh_ref_gallery()

    def _refresh_ref_gallery(self):
        while self.ref_inner_layout.count() > 1:
            item = self.ref_inner_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for fpath in self.selected_image_paths:
            pixmap = QPixmap(fpath)
            if pixmap.isNull():
                continue
            thumb = pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl = QLabel()
            lbl.setFixedSize(60, 60)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setPixmap(thumb)
            lbl.setStyleSheet("border: 1px solid #D4C9B8; border-radius: 3px; background: #FFFFFF;")
            lbl.setToolTip(os.path.basename(fpath))
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.setContextMenuPolicy(Qt.CustomContextMenu)
            lbl.customContextMenuRequested.connect(lambda pos, p=fpath: self._ref_context_menu(pos, p, lbl))
            self.ref_inner_layout.insertWidget(self.ref_inner_layout.count() - 1, lbl)

    def _ref_context_menu(self, pos, fpath, widget):
        menu = QMenu(self)
        menu.addAction("📋 读取生成参数", lambda: self._load_metadata_to_ui(fpath))
        menu.addAction("📋 查看生成参数", lambda: self._show_metadata_dialog(fpath))
        menu.addSeparator()
        menu.addAction("❌ 移除此图", lambda: self._remove_ref_image(fpath))
        menu.exec(widget.mapToGlobal(pos))

    def _remove_ref_image(self, fpath):
        if fpath in self.selected_image_paths:
            self.selected_image_paths.remove(fpath)
            self.ref_count_label.setText(f"{len(self.selected_image_paths)} files")
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
        while self.gallery_inner_layout.count() > 0:
            item = self.gallery_inner_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        to_delete = [tid for tid, d in self.task_store.items()
                     if "Running" not in d.get("status", "") and "Waiting" not in d.get("status", "")]
        for tid in to_delete:
            self._delete_task(tid)
        gc.collect()
        self.log("🧹 内存清理完毕")

    def _open_output_dir(self):
        d = self.current_settings.get("output_dir", "images")
        if not os.path.exists(d):
            os.makedirs(d)
        try:
            os.startfile(os.path.abspath(d))
        except Exception:
            pass

    def _update_char_count(self):
        text = self.prompt_text.toPlainText()
        self.lbl_char_count.setText(f"Len: {len(text)}")

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
        else:
            self.param1_label.setText("图像比例:")
            self.ratio_combo.addItems(list(self.ratio_map.keys()))
            self.ratio_combo.setCurrentIndex(min(self.current_settings.get("aspect_ratio_idx", 1), len(self.ratio_map) - 1))
            self.param2_label.setText("图像尺寸:")
            self.res_combo.addItems(["1K", "2K", "4K"])
            self.res_combo.setCurrentIndex(min(self.current_settings.get("resolution_idx", 2), 2))

        self.ratio_combo.blockSignals(False)
        self.res_combo.blockSignals(False)

    def _save_profile_changes(self):
        api_type = "gpt" if self.api_type_combo.currentIndex() == 1 else "gemini"
        self.cfg_mgr.update_profile(self.profile_combo.currentIndex(), api_type,
                                    self.api_url_entry.text(), self.api_key_entry.text(),
                                    self.model_entry.text())
        self.log("✅ Profile Updated")

    def _create_new_profile(self):
        name, ok = QInputDialog.getText(self, "新建配置", "配置名称:")
        if ok and name:
            api_type = "gpt" if self.api_type_combo.currentIndex() == 1 else "gemini"
            self.cfg_mgr.add_profile(name, api_type, self.api_url_entry.text(),
                                     self.api_key_entry.text(), self.model_entry.text())
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
        if self.current_preview_path and self.show_preview_cb.isChecked() and self._preview_pixmap_item:
            self.preview_view.fitInView(
                self.preview_scene.sceneRect(), Qt.KeepAspectRatio
            )
            self._zoom_level = 1.0

    def closeEvent(self, event):
        self.task_manager.active = False
        event.accept()
