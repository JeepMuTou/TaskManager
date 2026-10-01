from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QListWidget, QListWidgetItem, QPushButton, QLabel, 
                               QGroupBox, QCheckBox, QSpinBox, QMessageBox, QSplitter,
                               QRadioButton, QButtonGroup, QTimeEdit, QStackedWidget,
                               QSizePolicy, QScrollArea, QFrame, QLayout)
from PySide6.QtCore import Qt, QTime, QTimer
from app.gui.dynamic_form import DynamicForm
from app.core.task_manager import TaskManager
from app.core.scheduler import SchedulerManager
from app.utils.config_store import ConfigStore

class ElidedLabel(QLabel):
    """一个可以在宽度不足时自动显示省略号的 Label"""
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

class CustomListWidgetItem(QWidget):
    """自定义任务列表项，左侧为名称，右侧为启用/禁用开关"""
    def __init__(self, task_name, task_id, is_enabled, on_toggle_callback):
        super().__init__()
        self.task_id = task_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_name = ElidedLabel(f"{task_name} ({task_id})")
        # 允许文本框无限缩小，以便把多余空间留给右侧的按钮，触发省略号机制
        self.lbl_name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        self.chk_enable = QCheckBox("启用")
        self.chk_enable.setChecked(is_enabled)
        self.chk_enable.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        layout.addWidget(self.lbl_name)
        layout.addWidget(self.chk_enable)
        
        self.chk_enable.toggled.connect(lambda checked: on_toggle_callback(self.task_id, checked))

class MainWindow(QMainWindow):
    def __init__(self, task_manager: TaskManager, scheduler_manager: SchedulerManager, config_store: ConfigStore):
        super().__init__()
        self.task_manager = task_manager
        self.scheduler_manager = scheduler_manager
        self.config_store = config_store
        
        self.tasks_schema = []
        self.current_selected_task_id = None
        self.time_pickers = [] # 存储所有的 QTimeEdit 控件
        
        self.setWindowTitle("定时任务管理器 (Task Manager)")
        self.resize(950, 750)
        # 设置全局基础样式
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f6fa; }
            QListWidget { border: 1px solid #dcdde1; border-radius: 4px; background-color: #ffffff; outline: none; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #1e90ff; color: white; border-radius: 4px; }
            QListWidget::item:hover { background-color: #f1f2f6; }
        """)
        self.setup_ui()
        self.load_tasks()
        
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_task_status)
        self.status_timer.start(1000)
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #dcdde1; }")
        main_layout.addWidget(splitter)
        
        # --- 左侧面板：任务列表 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("可用任务列表 (右侧开关控制启停):"))
        self.task_list_widget = QListWidget()
        self.task_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.task_list_widget.itemClicked.connect(self.on_task_selected)
        left_layout.addWidget(self.task_list_widget)
        
        # --- 右侧面板：任务配置 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 10, 0)
        
        # 1. 任务信息区 (Card Style)
        self.info_group = QFrame()
        self.info_group.setObjectName("Card")
        self.info_group.setStyleSheet("""
            QFrame#Card { background-color: #ffffff; border: 1px solid #e1e1e8; border-radius: 8px; }
        """)
        info_layout = QVBoxLayout(self.info_group)
        info_layout.setContentsMargins(15, 15, 15, 15)
        # 标题栏水平布局
        title_layout = QHBoxLayout()
        self.lbl_task_name = QLabel("请在左侧选择任务")
        self.lbl_task_name.setStyleSheet("font-weight: bold; font-size: 18px; color: #2f3640;")
        
        self.lbl_task_status = QLabel("🟢 运行中")
        self.lbl_task_status.setStyleSheet("background-color: #eccc68; color: #2f3542; font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
        self.lbl_task_status.setVisible(False)
        
        title_layout.addWidget(self.lbl_task_name)
        title_layout.addWidget(self.lbl_task_status)
        title_layout.addStretch()
        
        self.lbl_task_desc = QLabel("任务描述将在这里显示")
        self.lbl_task_desc.setStyleSheet("color: #718093;")
        self.lbl_task_desc.setWordWrap(True)
        
        info_layout.addLayout(title_layout)
        info_layout.addWidget(self.lbl_task_desc)
        right_layout.addWidget(self.info_group)
        
        # 2. 调度设置区 (Card Style)
        self.schedule_group = QFrame()
        self.schedule_group.setObjectName("Card")
        self.schedule_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.schedule_group.setStyleSheet("""
            QFrame#Card { background-color: #ffffff; border: 1px solid #e1e1e8; border-radius: 8px; }
        """)
        schedule_layout = QVBoxLayout(self.schedule_group)
        schedule_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_schedule_title = QLabel("定时调度策略")
        lbl_schedule_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2f3640;")
        schedule_layout.addWidget(lbl_schedule_title)
        
        # 单选按钮组 (使用类似 Segmented Control 的扁平化样式)
        mode_layout = QHBoxLayout()
        self.radio_weekly = QRadioButton("每周特定时间")
        self.radio_interval = QRadioButton("固定时间间隔")
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_weekly)
        self.radio_group.addButton(self.radio_interval)
        self.radio_weekly.setChecked(True)
        mode_layout.addWidget(self.radio_weekly)
        mode_layout.addWidget(self.radio_interval)
        mode_layout.addStretch()
        schedule_layout.addLayout(mode_layout)
        
        # 调度参数面板 (堆叠布局)
        self.schedule_stack = QStackedWidget()
        
        # 2.1 间隔面板 (Index 0)
        panel_interval = QWidget()
        pi_layout = QHBoxLayout(panel_interval)
        pi_layout.setContentsMargins(0, 10, 0, 0)
        pi_layout.addWidget(QLabel("调度周期 (秒):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 86400 * 30)
        self.spin_interval.setValue(60)
        self.spin_interval.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        pi_layout.addWidget(self.spin_interval)
        pi_layout.addStretch()
        self.schedule_stack.addWidget(panel_interval)
        
        # 2.2 每周面板 (Index 1)
        panel_weekly = QWidget()
        pw_layout = QVBoxLayout(panel_weekly)
        pw_layout.setContentsMargins(0, 10, 0, 0)
        pw_layout.setSpacing(10)
        
        # Row 1: 星期拨片按钮 (Toggle Chips)
        days_layout = QHBoxLayout()
        self.day_checkboxes = {}
        days_map = [("周一", "mon"), ("周二", "tue"), ("周三", "wed"), ("周四", "thu"),
                    ("周五", "fri"), ("周六", "sat"), ("周日", "sun")]
                    
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
        
        # Row 2: 流式时间标签列表
        times_display_layout = QHBoxLayout()
        lbl_times = QLabel("执行时间:")
        lbl_times.setStyleSheet("color: #718093; font-weight: bold;")
        times_display_layout.addWidget(lbl_times)
        
        # 启用自动换行的 QListWidget 充当 FlowLayout
        self.times_list = QListWidget()
        self.times_list.setFlow(QListWidget.LeftToRight)
        self.times_list.setWrapping(True)  # 开启换行
        self.times_list.setResizeMode(QListWidget.Adjust) # 大小变化时重新排列
        self.times_list.setSpacing(5)
        self.times_list.setMinimumHeight(45)
        self.times_list.setMaximumHeight(100) # 给够换行的空间
        self.times_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.times_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.times_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; }
            QListWidget::item { background: transparent; }
            QListWidget::item:selected { background: transparent; }
        """)
        
        times_display_layout.addWidget(self.times_list)
        pw_layout.addLayout(times_display_layout)
        
        # Row 3: 增加时间的输入区
        add_time_layout = QHBoxLayout()
        self.input_time = QTimeEdit()
        self.input_time.setDisplayFormat("HH:mm")
        self.input_time.setStyleSheet("padding: 4px; border: 1px solid #dcdde1; border-radius: 4px;")
        
        self.btn_add_time = QPushButton(" + 添加执行时间 ")
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
        right_layout.addWidget(self.schedule_group)
        
        # 3. 动态参数表单区 (Card Style)
        self.params_group = QFrame()
        self.params_group.setObjectName("Card")
        self.params_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.params_group.setStyleSheet("""
            QFrame#Card { background-color: #ffffff; border: 1px solid #e1e1e8; border-radius: 8px; }
        """)
        params_layout = QVBoxLayout(self.params_group)
        params_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_params_title = QLabel("任务自定义参数")
        lbl_params_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #2f3640;")
        params_layout.addWidget(lbl_params_title)
        
        self.dynamic_form = DynamicForm()
        params_layout.addWidget(self.dynamic_form)
        right_layout.addWidget(self.params_group)
        
        # 4. 底部操作按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("保存配置")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #1e90ff; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
            QPushButton:hover { background-color: #70a1ff; }
        """)
        self.btn_save.clicked.connect(self.on_save_clicked)
        
        self.btn_run_now = QPushButton("立即运行")
        self.btn_run_now.setCursor(Qt.PointingHandCursor)
        self.btn_run_now.setStyleSheet("""
            QPushButton { background-color: #ff4757; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
            QPushButton:hover { background-color: #ff6b81; }
        """)
        self.btn_run_now.clicked.connect(self.on_run_now_clicked)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run_now)
        btn_layout.addWidget(self.btn_save)
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 650])
        
        self.set_right_panel_enabled(False)
        
    def update_task_status(self):
        if not self.current_selected_task_id:
            return
            
        is_running = self.task_manager.is_task_running(self.current_selected_task_id)
        if is_running:
            self.lbl_task_status.setVisible(True)
            if self.btn_run_now.isEnabled():
                self.btn_run_now.setEnabled(False)
                self.btn_run_now.setText("正在运行...")
                self.btn_run_now.setStyleSheet("""
                    QPushButton { background-color: #a4b0be; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
                """)
        else:
            self.lbl_task_status.setVisible(False)
            if not self.btn_run_now.isEnabled():
                self.btn_run_now.setEnabled(True)
                self.btn_run_now.setText("立即运行")
                self.btn_run_now.setStyleSheet("""
                    QPushButton { background-color: #ff4757; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
                    QPushButton:hover { background-color: #ff6b81; }
                """)
        
    def on_add_time_clicked(self):
        time_str = self.input_time.time().toString("HH:mm")
        self.add_time_chip(time_str)
        
    def add_time_chip(self, time_str):
        # 防重复
        for data in self.time_pickers:
            if data["time_str"] == time_str:
                return
                
        chip_widget = QWidget()
        chip_layout = QHBoxLayout(chip_widget)
        chip_layout.setContentsMargins(8, 4, 4, 4)
        chip_layout.setSpacing(4)
        chip_layout.setSizeConstraint(QLayout.SetFixedSize)
        chip_widget.setStyleSheet("""
            QWidget { background-color: #f1f2f6; border-radius: 12px; border: 1px solid #dcdde1; }
        """)
        
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
        # 让 Item 完全匹配 Chip 的实际尺寸
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
        self.schedule_group.setEnabled(enabled)
        self.params_group.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_run_now.setEnabled(enabled)
        
    def load_tasks(self):
        self.task_list_widget.clear()
        self.tasks_schema = self.task_manager.scan_tasks()
        
        for schema in self.tasks_schema:
            task_id = schema.get("task_id")
            name = schema.get("task_name", task_id)
            
            # 加载并恢复调度
            config = self.config_store.get_task_config(task_id)
            is_enabled = config.get("enabled", False)
            if is_enabled:
                self.scheduler_manager.schedule_task(task_id, config)
            
            item = QListWidgetItem(self.task_list_widget)
            item.setData(Qt.UserRole, schema)
            
            custom_widget = CustomListWidgetItem(name, task_id, is_enabled, self.on_task_toggled)
            # 宽度设为极小值（比如10），强迫 QListWidget 遵循视口宽度，而不是文本原始宽度，从而保证右侧按钮永远可见
            from PySide6.QtCore import QSize
            item.setSizeHint(QSize(10, custom_widget.sizeHint().height()))
            self.task_list_widget.setItemWidget(item, custom_widget)

    def on_task_toggled(self, task_id: str, is_enabled: bool):
        config = self.config_store.get_task_config(task_id)
        config["enabled"] = is_enabled
        self.config_store.save_task_config(task_id, config)
        self.scheduler_manager.schedule_task(task_id, config)

    def on_task_selected(self, item: QListWidgetItem):
        schema = item.data(Qt.UserRole)
        self.current_selected_task_id = schema.get("task_id")
        
        self.lbl_task_name.setText(schema.get("task_name", self.current_selected_task_id))
        self.lbl_task_desc.setText(schema.get("description", "无描述"))
        
        config = self.config_store.get_task_config(self.current_selected_task_id)
        
        # 恢复调度策略 UI
        schedule_type = config.get("schedule_type", "weekly") # 默认为 weekly
        if schedule_type == "interval":
            self.radio_interval.setChecked(True)
        else:
            self.radio_weekly.setChecked(True)
            
        self.spin_interval.setValue(config.get("interval_seconds", 60))
        
        weekly_conf = config.get("weekly_schedule", {})
        saved_days = weekly_conf.get("days", [])
        for val, chk in self.day_checkboxes.items():
            chk.setChecked(val in saved_days)
            
        # 清理旧的时间选择器
        self.clear_time_pickers()
        times = weekly_conf.get("times", [])
        if not times and "time" in weekly_conf:
            times = [weekly_conf["time"]]
            
        if not times:
            self.add_time_chip("00:00")
        else:
            for t in times:
                self.add_time_chip(t)
        
        # 构建动态参数表单
        saved_params = config.get("params", {})
        self.dynamic_form.build_form(schema.get("parameters", []), saved_params, self.current_selected_task_id, self.task_manager)
        
        self.set_right_panel_enabled(True)
        
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
                
        # 收集所有设定的时间
        selected_times = []
        for picker in self.time_pickers:
            time_str = picker["time_str"]
            # 简单去重
            if time_str not in selected_times:
                selected_times.append(time_str)
                
        config["weekly_schedule"] = {
            "days": selected_days,
            "times": selected_times
        }
        
        config["params"] = self.dynamic_form.get_values()
        
        # 保存并重新调度
        self.config_store.save_task_config(self.current_selected_task_id, config)
        self.scheduler_manager.schedule_task(self.current_selected_task_id, config)
            
        QMessageBox.information(self, "成功", "设置已保存。如果该任务当前为启用状态，新的调度策略已生效。")
        
    def on_run_now_clicked(self):
        if not self.current_selected_task_id:
            return
        params = self.dynamic_form.get_values()
        self.task_manager.execute_task(self.current_selected_task_id, params)
        # 立即更新一次 UI，不用等下一秒的 timer
        self.update_task_status()
