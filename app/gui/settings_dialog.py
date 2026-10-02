from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QFrame, QMessageBox,
                               QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt
from app.gui.main_window import IOSSwitch
from app.utils.settings_store import SettingsStore
from app.utils.i18n import tr


class SettingsDialog(QDialog):
    def __init__(self, settings_store: SettingsStore, parent=None):
        super().__init__(parent)
        self.settings_store = settings_store
        self.lang = settings_store.language
        
        self.setWindowTitle(tr("settings_title", self.lang))
        self.setFixedSize(400, 285)
        self.setStyleSheet("QDialog { background-color: #f5f6fa; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 3)
        layout.setSpacing(12)
        
        # --- Card ---
        card = QFrame()
        card.setObjectName("SettingsCard")
        card.setStyleSheet("QFrame#SettingsCard { background-color: #ffffff; border: 1px solid #e1e1e8; border-radius: 8px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(18)
        
        # 1. 语言
        lang_row = QHBoxLayout()
        self.lbl_language = QLabel(tr("settings_language", self.lang))
        self.lbl_language.setStyleSheet("font-weight: bold; font-size: 13px; color: #2f3640;")
        self.radio_zh = QRadioButton("中文")
        self.radio_en = QRadioButton("English")
        if self.lang == "en":
            self.radio_en.setChecked(True)
        else:
            self.radio_zh.setChecked(True)
            
        self.lang_group = QButtonGroup(self)
        self.lang_group.addButton(self.radio_zh)
        self.lang_group.addButton(self.radio_en)
        
        lang_opts_layout = QHBoxLayout()
        lang_opts_layout.addWidget(self.radio_zh)
        lang_opts_layout.addWidget(self.radio_en)
        
        lang_row.addWidget(self.lbl_language)
        lang_row.addStretch()
        lang_row.addLayout(lang_opts_layout)
        card_layout.addLayout(lang_row)
        
        # 2. 开机自启
        auto_row = QHBoxLayout()
        self.lbl_auto = QLabel(tr("settings_auto_start", self.lang))
        self.lbl_auto.setStyleSheet("font-weight: bold; font-size: 13px; color: #2f3640;")
        self.switch_auto = IOSSwitch()
        self.switch_auto.setChecked(settings_store.auto_start)
        if settings_store.auto_start:
            self.switch_auto._position = 1.0
        auto_row.addWidget(self.lbl_auto)
        auto_row.addStretch()
        auto_row.addWidget(self.switch_auto)
        card_layout.addLayout(auto_row)
        
        # 3. 关闭最小化
        tray_row = QHBoxLayout()
        self.lbl_tray = QLabel(tr("settings_minimize", self.lang))
        self.lbl_tray.setStyleSheet("font-weight: bold; font-size: 13px; color: #2f3640;")
        self.switch_tray = IOSSwitch()
        self.switch_tray.setChecked(settings_store.minimize_to_tray)
        if settings_store.minimize_to_tray:
            self.switch_tray._position = 1.0
        tray_row.addWidget(self.lbl_tray)
        tray_row.addStretch()
        tray_row.addWidget(self.switch_tray)
        card_layout.addLayout(tray_row)
        
        # 4. 允许任务并行
        parallel_row = QHBoxLayout()
        self.lbl_parallel = QLabel(tr("settings_parallel", self.lang))
        self.lbl_parallel.setStyleSheet("font-weight: bold; font-size: 13px; color: #2f3640;")
        self.switch_parallel = IOSSwitch()
        self.switch_parallel.setChecked(settings_store.allow_parallel_tasks)
        if settings_store.allow_parallel_tasks:
            self.switch_parallel._position = 1.0
        parallel_row.addWidget(self.lbl_parallel)
        parallel_row.addStretch()
        parallel_row.addWidget(self.switch_parallel)
        card_layout.addLayout(parallel_row)
        
        layout.addWidget(card)
        
        # --- Buttons ---
        btn_layout = QHBoxLayout()
        
        self.btn_auto_fix = QPushButton(tr("settings_auto_fix", self.lang))
        self.btn_auto_fix.setCursor(Qt.PointingHandCursor)
        self.btn_auto_fix.setStyleSheet("""
            QPushButton { background-color: #f1f2f6; border: 1px solid #dcdde1; border-radius: 6px; padding: 8px 20px; font-weight: bold; color: #e1b12c;}
            QPushButton:hover { background-color: #dcdde1; }
        """)
        self.btn_auto_fix.clicked.connect(self.on_auto_fix_clicked)
        btn_layout.addWidget(self.btn_auto_fix)
        
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton(tr("settings_cancel", self.lang))
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color: #f1f2f6; border: 1px solid #dcdde1; border-radius: 6px; padding: 8px 20px; font-weight: bold; color: #2f3542;}
            QPushButton:hover { background-color: #dcdde1; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton(tr("settings_save", self.lang))
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #1e90ff; color: white; border-radius: 6px; padding: 8px 20px; font-weight: bold;}
            QPushButton:hover { background-color: #70a1ff; }
        """)
        self.btn_save.clicked.connect(self.on_save)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        # --- Author & License Info ---
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(5, 0, 5, 0)
        
        lbl_author = QLabel("Author: JiaYunPeng")
        lbl_author.setStyleSheet("color: #a4b0be; font-size: 11px;")
        
        lbl_license = QLabel("Under GNU AGPL-3.0")
        lbl_license.setStyleSheet("color: #a4b0be; font-size: 11px;")
        
        info_layout.addWidget(lbl_author)
        info_layout.addStretch()
        info_layout.addWidget(lbl_license)
        
        # 将按钮区和底部版权区包裹在一起
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(8) # 这里的 8px 大概相当于半行的间距
        bottom_layout.addLayout(btn_layout)
        bottom_layout.addLayout(info_layout)
        
        layout.addLayout(bottom_layout)
    
    def on_save(self):
        self.settings_store.language = "en" if self.radio_en.isChecked() else "zh"
        self.settings_store.auto_start = self.switch_auto.isChecked()
        self.settings_store.minimize_to_tray = self.switch_tray.isChecked()
        self.settings_store.allow_parallel_tasks = self.switch_parallel.isChecked()
        self.settings_store.save()
        self.settings_store.apply_auto_start()
        
        QMessageBox.information(
            self,
            tr("settings_saved_title", self.settings_store.language),
            tr("settings_saved_msg", self.settings_store.language)
        )
        self.accept()

    def on_auto_fix_clicked(self):
        from app.core.env_manager import EnvManager
        from pathlib import Path
        
        # Determine tasks directory (assume next to data_dir)
        tasks_dir = self.settings_store.data_dir.parent / "tasks"
        env_mgr = EnvManager(str(tasks_dir))
        
        self.btn_auto_fix.setEnabled(False)
        self.btn_auto_fix.setText("Checking...")
        self.repaint()
        
        is_ok, missing_python, missing_libs = env_mgr.check_env()
        
        self.btn_auto_fix.setText(tr("settings_auto_fix", self.lang))
        self.btn_auto_fix.setEnabled(True)
        
        if is_ok:
            QMessageBox.information(self, "OK", tr("env_ok", self.lang))
        else:
            libs_str = "\n".join([f"- {lib}" for lib in missing_libs]) if missing_libs else ""
            msg = tr("env_missing", self.lang).replace("{libs}", libs_str)
            
            reply = QMessageBox.question(self, "Warning", msg, QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                env_mgr.start_auto_fix()
                QMessageBox.information(self, "Fixing", tr("env_fixing", self.lang))
