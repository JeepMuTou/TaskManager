from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QListWidget, QListWidgetItem, QPushButton, QLabel, 
                               QGroupBox, QCheckBox, QSpinBox, QMessageBox, QSplitter,
                               QRadioButton, QButtonGroup, QTimeEdit, QStackedWidget,
                               QSizePolicy, QScrollArea, QFrame, QLayout,
                               QSystemTrayIcon, QMenu)
from PySide6.QtCore import Qt, QTime, QTimer, Property, QPropertyAnimation, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QIcon, QAction
from app.core.task_manager import TaskManager
from app.core.scheduler import SchedulerManager
from app.utils.config_store import ConfigStore
from app.utils.settings_store import SettingsStore
from app.utils.i18n import tr

class ElidedLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.full_text = text
        self.setMinimumWidth(30)
        
    def setText(self, text):
        self.full_text = text
        super().setText(text)
        
    def resizeEvent(self, event):
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self.full_text, Qt.ElideRight, self.width())
        super().setText(elided)

class IOSSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._position = 0
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setDuration(150)
        self.stateChanged.connect(self.setup_animation)

    @Property(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(1.0)
        else:
            self.animation.setEndValue(0.0)
        self.animation.start()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        p = self._position
        
        # Colors
        if p == 0:
            bg_color = QColor("#e5e5ea")
        elif p == 1:
            bg_color = QColor("#34c759")
        else:
            r = int(229 + (52 - 229) * p)
            g = int(229 + (199 - 229) * p)
            b = int(234 + (89 - 234) * p)
            bg_color = QColor(r, g, b)
            
        thumb_color = QColor("#ffffff")
        
        rect = QRectF(0, 0, self.width(), self.height())
        radius = rect.height() / 2
        
        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, radius, radius)
        
        # Draw thumb
        margin = 2
        thumb_radius = radius - margin
        thumb_x = margin + p * (self.width() - 2 * margin - 2 * thumb_radius)
        thumb_y = margin
        
        thumb_rect = QRectF(thumb_x, thumb_y, 2 * thumb_radius, 2 * thumb_radius)
        
        # Drop shadow for thumb
        shadow_rect = thumb_rect.translated(0, 1)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawEllipse(shadow_rect)
        
        # Actual thumb
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(thumb_rect)

class CustomListWidgetItem(QWidget):
    def __init__(self, task_name, task_id, is_enabled, on_toggle_callback):
        super().__init__()
        self.task_id = task_id
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        self.lbl_name = ElidedLabel(f"{task_name} ({task_id})")
        self.lbl_name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        
        self.chk_enable = IOSSwitch()
        self.chk_enable.setChecked(is_enabled)
        if is_enabled:
            self.chk_enable._position = 1.0
        
        layout.addWidget(self.lbl_name)
        layout.addWidget(self.chk_enable)
        
        self.chk_enable.toggled.connect(lambda checked: on_toggle_callback(self.task_id, checked))

class MainWindow(QMainWindow):
    def __init__(self, task_manager: TaskManager, scheduler_manager: SchedulerManager, 
                 config_store: ConfigStore, settings_store: SettingsStore):
        super().__init__()
        self.task_manager = task_manager
        self.scheduler_manager = scheduler_manager
        self.config_store = config_store
        self.settings_store = settings_store
        self.lang = settings_store.language
        
        self.tasks_schema = []
        self.current_selected_task_id = None
        self.time_pickers = []
        self._force_quit = False
        
        self.setWindowTitle(tr("window_title", self.lang))
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f6fa; }
            QListWidget { border: 1px solid #dcdde1; border-radius: 4px; background-color: #ffffff; outline: none; }
            QListWidget::item { padding: 0px; margin: 0px; background-color: #ffffff; }
            QListWidget::item:selected { background-color: #1e90ff; color: white; border-radius: 4px; }
        """)
        self.setup_ui()
        self.load_tasks()
        self.setup_tray_icon()
        
        # 强制按内容自动调整大小，并锁死固定该大小 (禁用拖拽和最大化)
        # 为保证初始未选中任务时窗口高度不会被压缩，先强制显示一下调度区计算完整大小
        self.schedule_group.setVisible(True)
        self.adjustSize()
        self.setFixedSize(self.size())
        
        # 恢复实际状态
        if not self.current_selected_task_id:
            self.schedule_group.setVisible(False)
        
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_task_status)
        self.status_timer.start(1000)
    
    def setup_tray_icon(self):
        """初始化系统托盘图标"""
        import os
        self.tray_icon = QSystemTrayIcon(self)
        
        # 加载生成的图标
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.jpg")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            self.tray_icon.setIcon(icon)
            
        self.tray_icon.setToolTip(tr("window_title", self.lang))
        
        tray_menu = QMenu()
        action_show = QAction(tr("window_title", self.lang), self)
        action_show.triggered.connect(self.showNormal)
        action_quit = QAction("退出" if self.lang == "zh" else "Quit", self)
        action_quit.triggered.connect(self.force_quit)
        tray_menu.addAction(action_show)
        tray_menu.addSeparator()
        tray_menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()
    
    def force_quit(self):
        self._force_quit = True
        self.close()
    
    def closeEvent(self, event):
        if self.settings_store.minimize_to_tray and not self._force_quit:
            event.ignore()
            self.hide()
            self.tray_icon.show()
        else:
            self.tray_icon.hide()
            event.accept()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # --- 左侧面板：任务列表 ---
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        left_title_layout = QHBoxLayout()
        lbl_left_title = QLabel(tr("task_list_title", self.lang))
        lbl_left_title.setStyleSheet("font-weight: bold; color: #2f3640;")
        
        self.btn_app_config = QPushButton(tr("btn_app_config", self.lang))
        self.btn_app_config.setCursor(Qt.PointingHandCursor)
        self.btn_app_config.setStyleSheet("""
            QPushButton { background-color: #f1f2f6; border: 1px solid #dcdde1; border-radius: 4px; padding: 4px 8px; color: #2f3542;}
            QPushButton:hover { background-color: #eccc68; color: white; border-color: #eccc68;}
        """)
        self.btn_app_config.clicked.connect(self.on_app_config_clicked)
        
        left_title_layout.addWidget(lbl_left_title)
        left_title_layout.addStretch()
        left_title_layout.addWidget(self.btn_app_config)
        left_layout.addLayout(left_title_layout)
        
        self.task_list_widget = QListWidget()
        self.task_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.task_list_widget.itemClicked.connect(self.on_task_selected)
        left_layout.addWidget(self.task_list_widget)
        
        # --- 右侧面板：任务配置 ---
        right_panel = QWidget()
        right_panel.setFixedWidth(650)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 10, 0)
        
        # 1. 任务信息区
        self.info_group = QFrame()
        self.info_group.setObjectName("Card")
        self.info_group.setStyleSheet("QFrame#Card { background-color: #ffffff; border: 1px solid #e1e1e8; border-radius: 8px; }")
        info_layout = QVBoxLayout(self.info_group)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        title_layout = QHBoxLayout()
        self.lbl_task_name = QLabel(tr("select_task_hint", self.lang))
        self.lbl_task_name.setStyleSheet("font-weight: bold; font-size: 18px; color: #2f3640;")
        
        self.lbl_task_status = QLabel(tr("status_running", self.lang))
        self.lbl_task_status.setStyleSheet("background-color: #eccc68; color: #2f3542; font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
        self.lbl_task_status.setVisible(False)
        
        title_layout.addWidget(self.lbl_task_name)
        title_layout.addWidget(self.lbl_task_status)
        title_layout.addStretch()
        
        self.lbl_task_desc = QLabel(tr("desc_hint", self.lang))
        self.lbl_task_desc.setStyleSheet("color: #718093;")
        self.lbl_task_desc.setWordWrap(True)
        
        info_layout.addLayout(title_layout)
        info_layout.addWidget(self.lbl_task_desc)
        right_layout.addWidget(self.info_group)
        
        # 2. 调度设置区
        self.schedule_group = QFrame()
        self.schedule_group.setObjectName("Card")
        self.schedule_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.schedule_group.setStyleSheet("QFrame#Card { background-color: #ffffff; border: 1px solid #e1e1e8; border-radius: 8px; }")
        schedule_layout = QVBoxLayout(self.schedule_group)
        schedule_layout.setContentsMargins(15, 15, 15, 15)
        
        schedule_title_layout = QHBoxLayout()
        lbl_schedule_title = QLabel(tr("schedule_title", self.lang))
        lbl_schedule_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2f3640;")
        
        self.btn_configure_task = QPushButton(tr("btn_task_config", self.lang))
        self.btn_configure_task.setCursor(Qt.PointingHandCursor)
        self.btn_configure_task.setStyleSheet("""
            QPushButton { background-color: #9c88ff; color: white; border-radius: 4px; padding: 5px 15px; font-weight: bold;}
            QPushButton:hover { background-color: #8c7ae6; }
        """)
        self.btn_configure_task.clicked.connect(self.on_configure_task_clicked)
        
        schedule_title_layout.addWidget(lbl_schedule_title)
        schedule_title_layout.addStretch()
        schedule_title_layout.addWidget(self.btn_configure_task)
        schedule_layout.addLayout(schedule_title_layout)
        
        mode_layout = QHBoxLayout()
        self.radio_weekly = QRadioButton(tr("radio_weekly", self.lang))
        self.radio_interval = QRadioButton(tr("radio_interval", self.lang))
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_weekly)
        self.radio_group.addButton(self.radio_interval)
        self.radio_weekly.setChecked(True)
        mode_layout.addWidget(self.radio_weekly)
        mode_layout.addWidget(self.radio_interval)
        mode_layout.addStretch()
        schedule_layout.addLayout(mode_layout)
        
        self.schedule_stack = QStackedWidget()
        
        # 2.1 间隔面板
        panel_interval = QWidget()
        pi_layout = QHBoxLayout(panel_interval)
        pi_layout.setContentsMargins(0, 10, 0, 0)
        pi_layout.addWidget(QLabel(tr("interval_label", self.lang)))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 86400 * 30)
        self.spin_interval.setValue(60)
        self.spin_interval.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        pi_layout.addWidget(self.spin_interval)
        pi_layout.addStretch()
        self.schedule_stack.addWidget(panel_interval)
        
        # 2.2 每周面板
        panel_weekly = QWidget()
        pw_layout = QVBoxLayout(panel_weekly)
        pw_layout.setContentsMargins(0, 10, 0, 0)
        pw_layout.setSpacing(10)
        
        days_layout = QHBoxLayout()
        self.day_checkboxes = {}
        days_map = [(tr("day_mon", self.lang), "mon"), (tr("day_tue", self.lang), "tue"), 
                    (tr("day_wed", self.lang), "wed"), (tr("day_thu", self.lang), "thu"),
                    (tr("day_fri", self.lang), "fri"), (tr("day_sat", self.lang), "sat"), 
                    (tr("day_sun", self.lang), "sun")]
                    
        chip_qss = """
            QPushButton {
                background-color: #f1f2f6;
                border: 1px solid #dcdde1;
                border-radius: 12px;
                padding: 4px 10px;
                color: #718093;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #eccc68; color: #fff; border-color: #eccc68; }
            QPushButton:checked { background-color: #3742fa; color: white; border-color: #3742fa; }
        """
        for text, val in days_map:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setStyleSheet(chip_qss)
            btn.setCursor(Qt.PointingHandCursor)
            self.day_checkboxes[val] = btn
            days_layout.addWidget(btn)
        days_layout.addStretch()
        pw_layout.addLayout(days_layout)
        
        times_display_layout = QHBoxLayout()
        lbl_times = QLabel(tr("exec_time_label", self.lang))
        lbl_times.setStyleSheet("color: #718093; font-weight: bold;")
        times_display_layout.addWidget(lbl_times)
        
        self.times_list = QListWidget()
        self.times_list.setFlow(QListWidget.LeftToRight)
        self.times_list.setWrapping(True)
        self.times_list.setResizeMode(QListWidget.Adjust)
        self.times_list.setSpacing(5)
        self.times_list.setMinimumHeight(45)
        self.times_list.setMaximumHeight(100)
        self.times_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.times_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.times_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; }
            QListWidget::item { background: transparent; }
            QListWidget::item:selected { background: transparent; }
        """)
        
        times_display_layout.addWidget(self.times_list)
        pw_layout.addLayout(times_display_layout)
        
        add_time_layout = QHBoxLayout()
        self.input_time = QTimeEdit()
        self.input_time.setDisplayFormat("HH:mm")
        self.input_time.setStyleSheet("padding: 4px; border: 1px solid #dcdde1; border-radius: 4px;")
        
        self.btn_add_time = QPushButton(tr("btn_add_time", self.lang))
        self.btn_add_time.setCursor(Qt.PointingHandCursor)
        self.btn_add_time.setStyleSheet("""
            QPushButton {
                background-color: #2ed573;
                border-radius: 4px;
                padding: 5px 12px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7bed9f; }
            QPushButton:pressed { background-color: #2f3542; }
        """)
        self.btn_add_time.clicked.connect(self.on_add_time_clicked)
        
        add_time_layout.addWidget(self.input_time)
        add_time_layout.addWidget(self.btn_add_time)
        add_time_layout.addStretch()
        pw_layout.addLayout(add_time_layout)
        
        self.schedule_stack.addWidget(panel_weekly)
        self.schedule_stack.setCurrentIndex(1)
        self.radio_interval.toggled.connect(lambda: self.schedule_stack.setCurrentIndex(0))
        self.radio_weekly.toggled.connect(lambda: self.schedule_stack.setCurrentIndex(1))
        
        schedule_layout.addWidget(self.schedule_stack)
        
        # --- 全局超时强杀配置 (对所有调度模式生效) ---
        timeout_layout = QHBoxLayout()
        timeout_layout.setContentsMargins(0, 10, 0, 0)
        
        self.chk_timeout = QCheckBox(tr("timeout_prefix", self.lang))
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 99999999)
        self.spin_timeout.setValue(10)
        self.spin_timeout.setFixedWidth(80)
        self.lbl_timeout_suffix = QLabel(tr("timeout_suffix", self.lang))
        
        def on_timeout_toggled(checked):
            self.spin_timeout.setEnabled(checked)
            color = "#2f3640" if checked else "#a4b0be"
            self.chk_timeout.setStyleSheet(f"color: {color};")
            self.lbl_timeout_suffix.setStyleSheet(f"color: {color};")
        
        self.chk_timeout.toggled.connect(on_timeout_toggled)
        self.chk_timeout.setChecked(True)
        on_timeout_toggled(True)
        
        timeout_layout.addWidget(self.chk_timeout)
        timeout_layout.addWidget(self.spin_timeout)
        timeout_layout.addWidget(self.lbl_timeout_suffix)
        timeout_layout.addStretch()
        
        schedule_layout.addLayout(timeout_layout)
        

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        self.btn_save = QPushButton(tr("btn_save", self.lang))
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #1e90ff; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
            QPushButton:hover { background-color: #70a1ff; }
        """)
        self.btn_save.clicked.connect(self.on_save_clicked)
        
        self.btn_run_now = QPushButton(tr("btn_run_now", self.lang))
        self.btn_run_now.setCursor(Qt.PointingHandCursor)
        self.btn_run_now.setStyleSheet("""
            QPushButton { background-color: #ff4757; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
            QPushButton:hover { background-color: #ff6b81; }
        """)
        self.btn_run_now.clicked.connect(self.on_run_now_clicked)
        
        self.btn_stop_run = QPushButton(tr("btn_stop_run", self.lang))
        self.btn_stop_run.setCursor(Qt.PointingHandCursor)
        self.btn_stop_run.setStyleSheet("""
            QPushButton { background-color: #ff7f50; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
            QPushButton:hover { background-color: #ff9f43; }
        """)
        self.btn_stop_run.setVisible(False)
        self.btn_stop_run.clicked.connect(self.on_stop_run_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run_now)
        btn_layout.addWidget(self.btn_stop_run)
        btn_layout.addWidget(self.btn_save)
        schedule_layout.addLayout(btn_layout)
        
        right_layout.addWidget(self.schedule_group)
        
        right_layout.addStretch()
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.set_right_panel_enabled(False)
        
    def update_task_status(self):
        if not self.current_selected_task_id:
            return
            
        is_running = self.task_manager.is_task_running(self.current_selected_task_id)
        if is_running:
            self.lbl_task_status.setVisible(True)
            self.btn_stop_run.setVisible(True)
            if self.btn_run_now.isEnabled():
                self.btn_run_now.setEnabled(False)
                self.btn_run_now.setText(tr("btn_running", self.lang))
                self.btn_run_now.setStyleSheet("QPushButton { background-color: #a4b0be; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}")
        else:
            self.lbl_task_status.setVisible(False)
            self.btn_stop_run.setVisible(False)
            if not self.btn_run_now.isEnabled():
                self.btn_run_now.setEnabled(True)
                self.btn_run_now.setText(tr("btn_run_now", self.lang))
                self.btn_run_now.setStyleSheet("""
                    QPushButton { background-color: #ff4757; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
                    QPushButton:hover { background-color: #ff6b81; }
                """)
        
    def on_add_time_clicked(self):
        time_str = self.input_time.time().toString("HH:mm")
        self.add_time_chip(time_str)
        
    def add_time_chip(self, time_str):
        for data in self.time_pickers:
            if data["time_str"] == time_str:
                return
                
        chip_widget = QWidget()
        chip_layout = QHBoxLayout(chip_widget)
        chip_layout.setContentsMargins(8, 4, 4, 4)
        chip_layout.setSpacing(4)
        chip_layout.setSizeConstraint(QLayout.SetFixedSize)
        chip_widget.setStyleSheet("QWidget { background-color: #f1f2f6; border-radius: 12px; border: 1px solid #dcdde1; }")
        
        lbl = QLabel(time_str)
        lbl.setStyleSheet("color: #2f3542; font-weight: bold; border: none; background: transparent;")
        
        btn_remove = QPushButton("×")
        btn_remove.setFixedSize(18, 18)
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setStyleSheet("""
            QPushButton { border: none; border-radius: 9px; font-weight: bold; color: white; background-color: #ff4757; font-size: 14px; padding-bottom: 2px;}
            QPushButton:hover { background-color: #ff6b81; }
        """)
        
        chip_layout.addWidget(lbl)
        chip_layout.addWidget(btn_remove)
        
        item = QListWidgetItem()
        item.setSizeHint(chip_widget.sizeHint())
        self.times_list.addItem(item)
        self.times_list.setItemWidget(item, chip_widget)
        
        picker_data = {"item": item, "time_str": time_str}
        self.time_pickers.append(picker_data)
        
        btn_remove.clicked.connect(lambda: self.remove_time_picker(picker_data))

    def remove_time_picker(self, picker_data):
        self.time_pickers.remove(picker_data)
        item = picker_data["item"]
        row = self.times_list.row(item)
        self.times_list.takeItem(row)

    def clear_time_pickers(self):
        self.times_list.clear()
        self.time_pickers.clear()

    def set_right_panel_enabled(self, enabled: bool):
        self.info_group.setEnabled(enabled)
        # 未选择任务时，直接隐藏下方的调度策略和按钮组，避免画面空洞和误操作
        self.schedule_group.setVisible(enabled)
        
    def load_tasks(self):
        self.task_list_widget.clear()
        self.tasks_schema = self.task_manager.scan_tasks()
        
        for schema in self.tasks_schema:
            task_id = schema.get("task_id")
            name = schema.get("name", task_id)
            if isinstance(name, dict):
                name = name.get(self.lang, name.get("zh", task_id))
            
            config = self.config_store.get_task_config(task_id)
            is_enabled = config.get("enabled", False)
            if is_enabled:
                self.scheduler_manager.schedule_task(task_id, config)
            
            item = QListWidgetItem(self.task_list_widget)
            item.setData(Qt.UserRole, schema)
            
            custom_widget = CustomListWidgetItem(name, task_id, is_enabled, self.on_task_toggled)
            from PySide6.QtCore import QSize
            item.setSizeHint(QSize(10, custom_widget.maximumHeight()))
            self.task_list_widget.setItemWidget(item, custom_widget)

    def on_task_toggled(self, task_id: str, is_enabled: bool):
        # 自动选中该任务
        for i in range(self.task_list_widget.count()):
            item = self.task_list_widget.item(i)
            schema = item.data(Qt.UserRole)
            if schema and schema.get("task_id") == task_id:
                self.task_list_widget.setCurrentItem(item)
                self.on_task_selected(item)
                break
        
        config = self.config_store.get_task_config(task_id)
        config["enabled"] = is_enabled
        self.config_store.save_task_config(task_id, config)
        self.scheduler_manager.schedule_task(task_id, config)

    def on_app_config_clicked(self):
        from app.gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.settings_store, self)
        if dialog.exec():
            # 语言可能已更改，提示用户重启
            pass

    def on_task_selected(self, item: QListWidgetItem):
        schema = item.data(Qt.UserRole)
        self.current_selected_task_id = schema.get("task_id")
        
        # 支持双语 name/description
        name = schema.get("name", self.current_selected_task_id)
        if isinstance(name, dict):
            name = name.get(self.lang, name.get("zh", self.current_selected_task_id))
        
        desc = schema.get("description", tr("no_desc", self.lang))
        if isinstance(desc, dict):
            desc = desc.get(self.lang, desc.get("zh", tr("no_desc", self.lang)))
        
        self.lbl_task_name.setText(name)
        self.lbl_task_desc.setText(desc)
        
        config = self.config_store.get_task_config(self.current_selected_task_id)
        
        schedule_type = config.get("schedule_type", "weekly")
        if schedule_type == "interval":
            self.radio_interval.setChecked(True)
        else:
            self.radio_weekly.setChecked(True)
            
        self.spin_interval.setValue(config.get("interval_seconds", 60))
        
        weekly_conf = config.get("weekly_schedule", {})
        saved_days = weekly_conf.get("days", [])
        for val, chk in self.day_checkboxes.items():
            chk.setChecked(val in saved_days)
            
        self.clear_time_pickers()
        times = weekly_conf.get("times", [])
        if not times and "time" in weekly_conf:
            times = [weekly_conf["time"]]
            
        if not times:
            self.add_time_chip("00:00")
        else:
            for t in times:
                self.add_time_chip(t)
                
        self.chk_timeout.setChecked(config.get("timeout_enabled", True))
        self.spin_timeout.setValue(config.get("timeout_minutes", 10))
        
        self.set_right_panel_enabled(True)
        # 切换任务时立即刷新运行状态，消除定时器延迟带来的视觉残留
        self.update_task_status()
        
    def on_configure_task_clicked(self):
        if not self.current_selected_task_id:
            return
        self.task_manager.open_task_config(self.current_selected_task_id)
        
    def on_save_clicked(self):
        if not self.current_selected_task_id:
            return
            
        config = self.config_store.get_task_config(self.current_selected_task_id)
        
        if self.radio_weekly.isChecked():
            config["schedule_type"] = "weekly"
        else:
            config["schedule_type"] = "interval"
            
        config["interval_seconds"] = self.spin_interval.value()
        
        selected_days = []
        for val, chk in self.day_checkboxes.items():
            if chk.isChecked():
                selected_days.append(val)
                
        selected_times = []
        for picker in self.time_pickers:
            time_str = picker["time_str"]
            if time_str not in selected_times:
                selected_times.append(time_str)
                
        config["weekly_schedule"] = {
            "days": selected_days,
            "times": selected_times
        }
        
        config["timeout_enabled"] = self.chk_timeout.isChecked()
        config["timeout_minutes"] = self.spin_timeout.value()
        
        # params shouldn't be touched by main app anymore, it is managed by the task config UI
        # But we write the rest of the config.
        
        self.config_store.save_task_config(self.current_selected_task_id, config)
        self.scheduler_manager.schedule_task(self.current_selected_task_id, config)
            
        QMessageBox.information(self, tr("save_success_title", self.lang), tr("save_success_msg", self.lang))
        
    def on_run_now_clicked(self):
        if not self.current_selected_task_id:
            return
        # Run without passing explicit params. Run.py reads them itself.
        self.task_manager.execute_task(self.current_selected_task_id)
        self.update_task_status()
        
    def on_stop_run_clicked(self):
        if not self.current_selected_task_id:
            return
        self.task_manager.kill_task(self.current_selected_task_id)
        self.update_task_status()
