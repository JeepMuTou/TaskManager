import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QTextEdit, QPushButton, QSpinBox, QMessageBox, 
    QGroupBox, QFormLayout, QCheckBox, QRadioButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt

# 尝试导入弹窗用于直接预览
try:
    from run import ExerciseReminderWindow
except ImportError:
    ExerciseReminderWindow = None

CONFIG_FILE = "config.json"

DEFAULT_PARAMS = {
    "title": "运动提醒",
    "content": "该去运动啦！站起来活动一下身体，伸展筋骨，保护颈椎与视力！",
    "sound": True,
    "snooze": True,
    "auto_close_seconds": 0,
    "lang": "zh"
}

TRANSLATIONS = {
    "window_title": {"zh": "运动提醒配置", "en": "Exercise Reminder Configuration"},
    "header_title": {"zh": "运动提醒任务设置", "en": "Exercise Reminder Settings"},
    "header_desc": {"zh": "在此自定义提醒弹窗的标题、显示内容与交互行为。", "en": "Customize the title, message, and behavior of the reminder popup."},
    "group_content": {"zh": "弹窗内容配置", "en": "Popup Content Configuration"},
    "lbl_title": {"zh": "弹窗标题:", "en": "Popup Title:"},
    "placeholder_title": {"zh": "例如：运动提醒、起身活动、伸展筋骨", "en": "e.g. Exercise Reminder, Stretch Break"},
    "lbl_content": {"zh": "显示内容:", "en": "Popup Content:"},
    "placeholder_content": {"zh": "输入要在弹窗中展示的提醒文字...", "en": "Enter the reminder text to be displayed in the popup..."},
    "group_options": {"zh": "弹窗行为设置", "en": "Popup Behavior Settings"},
    "chk_sound": {"zh": "弹窗弹出时播放系统提示音", "en": "Play alert sound when popup appears"},
    "chk_snooze": {"zh": "显示【稍后提醒 (5分钟)】按钮", "en": "Show [Snooze (5 mins)] button"},
    "lbl_auto_close": {"zh": "自动关闭等待时间 (秒，0表示不自动关闭):", "en": "Auto-close countdown (seconds, 0 for off):"},
    "btn_preview": {"zh": "👀 预览弹窗效果", "en": "👀 Preview Popup"},
    "btn_restore": {"zh": "恢复默认", "en": "Restore Defaults"},
    "btn_save": {"zh": "💾 保存配置", "en": "💾 Save Configuration"},
    "save_success": {"zh": "保存成功", "en": "Success"},
    "save_success_msg": {"zh": "运动提醒配置已成功保存！", "en": "Exercise reminder settings saved successfully!"},
    "save_error": {"zh": "保存失败", "en": "Save Error"},
    "save_error_msg": {"zh": "保存配置失败: {e}", "en": "Failed to save configuration: {e}"},
    "load_error": {"zh": "加载失败", "en": "Load Error"},
    "load_error_msg": {"zh": "加载现有配置失败: {e}", "en": "Failed to load configuration: {e}"},
}

def tr(key, lang):
    return TRANSLATIONS.get(key, {}).get(lang, key)

class ExerciseConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "zh"
        self.full_config = {}
        self.preview_window = None

        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle(tr("window_title", self.lang))
        self.resize(520, 480)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                font-size: 13px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #2f3640;
            }
            QLineEdit, QTextEdit, QSpinBox {
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: #ffffff;
                color: #2f3640;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border-color: #10b981;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 头部 Card
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(12, 10, 12, 10)

        header_info = QVBoxLayout()
        header_info.setSpacing(4)
        self.lbl_head_title = QLabel(tr("header_title", self.lang))
        self.lbl_head_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        self.lbl_head_desc = QLabel(tr("header_desc", self.lang))
        self.lbl_head_desc.setStyleSheet("font-size: 12px; color: #64748b;")
        header_info.addWidget(self.lbl_head_title)
        header_info.addWidget(self.lbl_head_desc)
        header_layout.addLayout(header_info)
        header_layout.addStretch()

        # 语言切换
        lang_layout = QHBoxLayout()
        self.radio_zh = QRadioButton("中文")
        self.radio_en = QRadioButton("English")
        self.radio_zh.setChecked(True)
        self.radio_zh.toggled.connect(self.on_lang_changed)
        lang_group = QButtonGroup(self)
        lang_group.addButton(self.radio_zh)
        lang_group.addButton(self.radio_en)
        lang_layout.addWidget(self.radio_zh)
        lang_layout.addWidget(self.radio_en)
        header_layout.addLayout(lang_layout)

        layout.addWidget(header_card)

        # 1. 弹窗内容配置
        self.group_content = QGroupBox(tr("group_content", self.lang))
        content_layout = QFormLayout(self.group_content)
        content_layout.setContentsMargins(14, 16, 14, 14)
        content_layout.setSpacing(10)

        self.lbl_field_title = QLabel(tr("lbl_title", self.lang))
        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText(tr("placeholder_title", self.lang))
        content_layout.addRow(self.lbl_field_title, self.input_title)

        self.lbl_field_content = QLabel(tr("lbl_content", self.lang))
        self.input_content = QTextEdit()
        self.input_content.setPlaceholderText(tr("placeholder_content", self.lang))
        self.input_content.setMinimumHeight(90)
        content_layout.addRow(self.lbl_field_content, self.input_content)

        layout.addWidget(self.group_content)

        # 2. 行为配置
        self.group_options = QGroupBox(tr("group_options", self.lang))
        options_layout = QVBoxLayout(self.group_options)
        options_layout.setContentsMargins(14, 16, 14, 14)
        options_layout.setSpacing(10)

        self.chk_sound = QCheckBox(tr("chk_sound", self.lang))
        self.chk_sound.setChecked(True)
        options_layout.addWidget(self.chk_sound)

        self.chk_snooze = QCheckBox(tr("chk_snooze", self.lang))
        self.chk_snooze.setChecked(True)
        options_layout.addWidget(self.chk_snooze)

        auto_close_row = QHBoxLayout()
        self.lbl_auto_close = QLabel(tr("lbl_auto_close", self.lang))
        self.spin_auto_close = QSpinBox()
        self.spin_auto_close.setRange(0, 3600)
        self.spin_auto_close.setSuffix(" 秒")
        self.spin_auto_close.setValue(0)
        auto_close_row.addWidget(self.lbl_auto_close)
        auto_close_row.addWidget(self.spin_auto_close)
        auto_close_row.addStretch()
        options_layout.addLayout(auto_close_row)

        layout.addWidget(self.group_options)

        # 底部按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_preview = QPushButton(tr("btn_preview", self.lang))
        self.btn_preview.setCursor(Qt.PointingHandCursor)
        self.btn_preview.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 9px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.btn_preview.clicked.connect(self.preview_popup)
        btn_layout.addWidget(self.btn_preview)

        self.btn_restore = QPushButton(tr("btn_restore", self.lang))
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 9px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        self.btn_restore.clicked.connect(self.restore_defaults)
        btn_layout.addWidget(self.btn_restore)

        btn_layout.addStretch()

        self.btn_save = QPushButton(tr("btn_save", self.lang))
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 9px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        self.btn_save.clicked.connect(self.save_config)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def on_lang_changed(self):
        self.lang = "zh" if self.radio_zh.isChecked() else "en"
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(tr("window_title", self.lang))
        self.lbl_head_title.setText(tr("header_title", self.lang))
        self.lbl_head_desc.setText(tr("header_desc", self.lang))
        self.group_content.setTitle(tr("group_content", self.lang))
        self.lbl_field_title.setText(tr("lbl_title", self.lang))
        self.input_title.setPlaceholderText(tr("placeholder_title", self.lang))
        self.lbl_field_content.setText(tr("lbl_content", self.lang))
        self.input_content.setPlaceholderText(tr("placeholder_content", self.lang))
        self.group_options.setTitle(tr("group_options", self.lang))
        self.chk_sound.setText(tr("chk_sound", self.lang))
        self.chk_snooze.setText(tr("chk_snooze", self.lang))
        self.lbl_auto_close.setText(tr("lbl_auto_close", self.lang))
        self.spin_auto_close.setSuffix(" s" if self.lang == "en" else " 秒")
        self.btn_preview.setText(tr("btn_preview", self.lang))
        self.btn_restore.setText(tr("btn_restore", self.lang))
        self.btn_save.setText(tr("btn_save", self.lang))

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.full_config = json.load(f)
                    params = self.full_config.get("params", {})
                    
                    self.input_title.setText(params.get("title", DEFAULT_PARAMS["title"]))
                    self.input_content.setPlainText(params.get("content", DEFAULT_PARAMS["content"]))
                    self.chk_sound.setChecked(params.get("sound", DEFAULT_PARAMS["sound"]))
                    self.chk_snooze.setChecked(params.get("snooze", DEFAULT_PARAMS["snooze"]))
                    self.spin_auto_close.setValue(int(params.get("auto_close_seconds", DEFAULT_PARAMS["auto_close_seconds"])))
                    
                    lang = params.get("lang", "zh")
                    if lang == "en":
                        self.radio_en.setChecked(True)
                    else:
                        self.radio_zh.setChecked(True)
                    self.lang = lang
                    self.retranslate_ui()
            except Exception as e:
                QMessageBox.warning(self, tr("load_error", self.lang), tr("load_error_msg", self.lang).replace("{e}", str(e)))
        else:
            self.restore_defaults()

    def restore_defaults(self):
        self.input_title.setText(DEFAULT_PARAMS["title"])
        self.input_content.setPlainText(DEFAULT_PARAMS["content"])
        self.chk_sound.setChecked(DEFAULT_PARAMS["sound"])
        self.chk_snooze.setChecked(DEFAULT_PARAMS["snooze"])
        self.spin_auto_close.setValue(DEFAULT_PARAMS["auto_close_seconds"])

    def preview_popup(self):
        title = self.input_title.text().strip() or "运动提醒"
        content = self.input_content.toPlainText().strip() or "该去运动啦！站起来活动一下身体，伸展筋骨，保护颈椎与视力！"
        sound = self.chk_sound.isChecked()
        snooze = self.chk_snooze.isChecked()
        auto_close = self.spin_auto_close.value()

        if ExerciseReminderWindow:
            if self.preview_window:
                self.preview_window.close()
            self.preview_window = ExerciseReminderWindow(
                title=title,
                content=content,
                sound=sound,
                snooze=snooze,
                auto_close_seconds=auto_close,
                is_preview=True
            )
            self.preview_window.bring_to_front()
            self.preview_window.play_sound()
        else:
            QMessageBox.information(self, "预览", f"【{title}】\n\n{content}")

    def save_config(self):
        title = self.input_title.text().strip() or DEFAULT_PARAMS["title"]
        content = self.input_content.toPlainText().strip() or DEFAULT_PARAMS["content"]
        
        params = {
            "title": title,
            "content": content,
            "sound": self.chk_sound.isChecked(),
            "snooze": self.chk_snooze.isChecked(),
            "auto_close_seconds": self.spin_auto_close.value(),
            "lang": self.lang
        }

        config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        
        # 1. 尝试读取现存全局配置（保护主程序调度参数）
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.full_config = json.load(f)
            except Exception:
                pass

        # 2. 仅更新 params 节点
        self.full_config["params"] = params

        # 3. 整体写回
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.full_config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, tr("save_success", self.lang), tr("save_success_msg", self.lang))
        except Exception as e:
            QMessageBox.critical(self, tr("save_error", self.lang), tr("save_error_msg", self.lang).replace("{e}", str(e)))

def main():
    app = QApplication(sys.argv)
    window = ExerciseConfigWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
