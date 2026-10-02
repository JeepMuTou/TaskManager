import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QTextEdit, QPushButton, QSpinBox, QMessageBox, QGroupBox, QFormLayout,
    QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt

CONFIG_FILE = "config.json"

TRANSLATIONS = {
    "window_title": {"zh": "Outlook 阅读器配置", "en": "Outlook Reader Configuration"},
    "stats_group": {"zh": "当前记录统计", "en": "Record Statistics"},
    "form_group": {"zh": "任务参数", "en": "Task Parameters"},
    "placeholder_target": {"zh": "监控邮箱账户，每行一个", "en": "Target email accounts, one per line"},
    "btn_detect": {"zh": "自动检测本机账户", "en": "Auto Detect Accounts"},
    "btn_open_target": {"zh": "打开配置文档", "en": "Open Config File"},
    "lbl_target": {"zh": "监控邮箱账户\n(每行一个):", "en": "Target Accounts\n(One per line):"},
    "placeholder_exclude": {"zh": "排除邮箱列表，每行一个邮箱", "en": "Exclude email list, one per line"},
    "btn_open_exclude": {"zh": "打开配置文档", "en": "Open Config File"},
    "lbl_exclude": {"zh": "排除邮箱列表\n(每行一个):", "en": "Exclude Emails\n(One per line):"},
    "lbl_past_hours": {"zh": "读取过去 N 小时内:", "en": "Read past N hours:"},
    "lbl_no_response": {"zh": "未回复门限 (秒):", "en": "No Response Threshold (s):"},
    "lbl_max_emails": {"zh": "单次最多读取封数:", "en": "Max Emails per read:"},
    "lbl_retention": {"zh": "最大保存上限 (小时):", "en": "Max Retention (hours):"},
    "btn_save": {"zh": "保存配置", "en": "Save Config"},
    "stats_none": {"zh": "尚未生成 Excel 数据文件。", "en": "No Excel data file generated yet."},
    "stats_count": {"zh": "本地 Excel 现已记录了 {count} 封邮件。", "en": "Local Excel currently records {count} emails."},
    "stats_no_openpyxl": {"zh": "未安装 openpyxl 库。", "en": "openpyxl library not installed."},
    "stats_fail": {"zh": "读取 Excel 失败: {e}", "en": "Failed to read Excel: {e}"},
    "detect_success": {"zh": "检测成功", "en": "Detection Success"},
    "detect_success_msg": {"zh": "检测到以下账户:\n{accounts}", "en": "Detected accounts:\n{accounts}"},
    "detect_warn": {"zh": "提示", "en": "Notice"},
    "detect_warn_msg": {"zh": "没有检测到邮箱账户，请确认您使用的是经典版 Outlook 并已登录。", "en": "No email accounts detected. Please ensure you use Classic Outlook and are logged in."},
    "detect_err_lib": {"zh": "未安装 pywin32 库。请执行 pip install pywin32", "en": "pywin32 not installed. Please run pip install pywin32"},
    "error": {"zh": "错误", "en": "Error"},
    "warning": {"zh": "警告", "en": "Warning"},
    "open_fail": {"zh": "无法打开配置文档: {e}", "en": "Cannot open config document: {e}"},
    "save_success": {"zh": "成功", "en": "Success"},
    "save_success_msg": {"zh": "配置保存成功！", "en": "Configuration saved successfully!"},
    "load_fail": {"zh": "加载失败", "en": "Load Failed"},
    "load_fail_msg": {"zh": "加载配置失败: {e}", "en": "Failed to load config: {e}"},
    "save_fail_msg": {"zh": "保存配置失败: {e}", "en": "Failed to save config: {e}"},
}

def tr(key, lang):
    return TRANSLATIONS.get(key, {}).get(lang, key)

class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "zh"
        self.full_config = {}
        
        self.resize(500, 350)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Statistics group
        self.stats_group = QGroupBox()
        self.stats_layout = QVBoxLayout(self.stats_group)
        self.lbl_stats = QLabel()
        self.stats_layout.addWidget(self.lbl_stats)
        self.layout.addWidget(self.stats_group)

        # Form group
        self.form_group = QGroupBox()
        self.form_layout = QFormLayout(self.form_group)
        
        # Target accounts
        self.account_layout = QHBoxLayout()
        self.input_target_account = QTextEdit()
        self.input_target_account.setMaximumHeight(80)
        self.account_layout.addWidget(self.input_target_account)
        
        account_btn_layout = QVBoxLayout()
        self.btn_detect = QPushButton()
        self.btn_detect.clicked.connect(self.detect_accounts)
        self.btn_open_target = QPushButton()
        self.btn_open_target.clicked.connect(lambda: self.open_txt_file("target_accounts.txt", self.input_target_account))
        account_btn_layout.addWidget(self.btn_detect)
        account_btn_layout.addWidget(self.btn_open_target)
        account_btn_layout.addStretch()
        self.account_layout.addLayout(account_btn_layout)
        
        self.lbl_target_row = QLabel()
        self.form_layout.addRow(self.lbl_target_row, self.account_layout)
        
        # Exclude emails
        self.exclude_layout = QHBoxLayout()
        self.input_exclude_emails = QTextEdit()
        self.input_exclude_emails.setMaximumHeight(80)
        self.exclude_layout.addWidget(self.input_exclude_emails)
        
        exclude_btn_layout = QVBoxLayout()
        self.btn_open_exclude = QPushButton()
        self.btn_open_exclude.clicked.connect(lambda: self.open_txt_file("exclude_emails.txt", self.input_exclude_emails))
        exclude_btn_layout.addWidget(self.btn_open_exclude)
        exclude_btn_layout.addStretch()
        self.exclude_layout.addLayout(exclude_btn_layout)
        
        self.lbl_exclude_row = QLabel()
        self.form_layout.addRow(self.lbl_exclude_row, self.exclude_layout)
        
        # Past hours
        self.spin_past_hours = QSpinBox()
        self.spin_past_hours.setRange(1, 8760)
        self.spin_past_hours.setValue(24)
        self.lbl_past_hours_row = QLabel()
        self.form_layout.addRow(self.lbl_past_hours_row, self.spin_past_hours)
        
        # No response threshold
        self.spin_no_response_threshold = QSpinBox()
        self.spin_no_response_threshold.setRange(0, 9999999)
        self.spin_no_response_threshold.setValue(0)
        self.lbl_no_response_row = QLabel()
        self.form_layout.addRow(self.lbl_no_response_row, self.spin_no_response_threshold)
        
        # Max emails
        self.spin_max_emails = QSpinBox()
        self.spin_max_emails.setRange(1, 100000)
        self.spin_max_emails.setValue(500)
        self.lbl_max_emails_row = QLabel()
        self.form_layout.addRow(self.lbl_max_emails_row, self.spin_max_emails)
        
        # Retention hours
        self.spin_retention_hours = QSpinBox()
        self.spin_retention_hours.setRange(1, 87600)
        self.spin_retention_hours.setValue(720)
        self.lbl_retention_row = QLabel()
        self.form_layout.addRow(self.lbl_retention_row, self.spin_retention_hours)
        
        self.layout.addWidget(self.form_group)
        self.layout.addStretch()

        # Action Buttons
        self.btn_layout = QHBoxLayout()
        
        self.radio_group_lang = QButtonGroup(self)
        self.radio_zh = QRadioButton("中文")
        self.radio_en = QRadioButton("English")
        self.radio_zh.setChecked(True)
        self.radio_group_lang.addButton(self.radio_zh)
        self.radio_group_lang.addButton(self.radio_en)
        
        self.radio_zh.toggled.connect(self.on_lang_changed)
        
        self.btn_layout.addWidget(self.radio_zh)
        self.btn_layout.addWidget(self.radio_en)
        self.btn_layout.addStretch()
        
        self.btn_save = QPushButton()
        self.btn_save.setMinimumWidth(100)
        self.btn_save.clicked.connect(self.save_config)
        self.btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(self.btn_layout)

        self.load_config()
        self.update_texts()
        self.update_stats()
        
    def on_lang_changed(self):
        self.lang = "zh" if self.radio_zh.isChecked() else "en"
        self.update_texts()
        self.update_stats()
        
    def update_texts(self):
        self.setWindowTitle(tr("window_title", self.lang))
        self.stats_group.setTitle(tr("stats_group", self.lang))
        self.form_group.setTitle(tr("form_group", self.lang))
        self.input_target_account.setPlaceholderText(tr("placeholder_target", self.lang))
        self.btn_detect.setText(tr("btn_detect", self.lang))
        self.btn_open_target.setText(tr("btn_open_target", self.lang))
        self.lbl_target_row.setText(tr("lbl_target", self.lang))
        
        self.input_exclude_emails.setPlaceholderText(tr("placeholder_exclude", self.lang))
        self.btn_open_exclude.setText(tr("btn_open_exclude", self.lang))
        self.lbl_exclude_row.setText(tr("lbl_exclude", self.lang))
        
        self.lbl_past_hours_row.setText(tr("lbl_past_hours", self.lang))
        self.lbl_no_response_row.setText(tr("lbl_no_response", self.lang))
        self.lbl_max_emails_row.setText(tr("lbl_max_emails", self.lang))
        self.lbl_retention_row.setText(tr("lbl_retention", self.lang))
        self.btn_save.setText(tr("btn_save", self.lang))

    def update_stats(self):
        excel_file = os.path.join(os.path.dirname(__file__), "data", "OriginalMail.xlsx")
        if not os.path.exists(excel_file):
            self.lbl_stats.setText(tr("stats_none", self.lang))
            return
        try:
            import openpyxl
            wb = openpyxl.load_workbook(excel_file, read_only=True)
            ws = wb.active
            count = ws.max_row - 1
            if count < 0: count = 0
            self.lbl_stats.setText(tr("stats_count", self.lang).replace("{count}", str(count)))
        except ImportError:
            self.lbl_stats.setText(tr("stats_no_openpyxl", self.lang))
        except Exception as e:
            self.lbl_stats.setText(tr("stats_fail", self.lang).replace("{e}", str(e)))

    def detect_accounts(self):
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            accounts = []
            for account in namespace.Accounts:
                accounts.append(account.DisplayName)
            if accounts:
                self.input_target_account.setPlainText("\n".join(accounts))
                msg = tr("detect_success_msg", self.lang).replace("{accounts}", chr(10).join(accounts))
                QMessageBox.information(self, tr("detect_success", self.lang), msg)
            else:
                QMessageBox.warning(self, tr("detect_warn", self.lang), tr("detect_warn_msg", self.lang))
        except ImportError:
            QMessageBox.critical(self, tr("error", self.lang), tr("detect_err_lib", self.lang))
        except Exception as e:
            QMessageBox.critical(self, tr("error", self.lang), f"{e}")

    def open_txt_file(self, filename, text_widget):
        filepath = os.path.join(os.path.dirname(__file__), filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text_widget.toPlainText())
            os.startfile(filepath)
        except Exception as e:
            QMessageBox.warning(self, tr("warning", self.lang), tr("open_fail", self.lang).replace("{e}", str(e)))

    def load_txt_files(self):
        target_file = os.path.join(os.path.dirname(__file__), "target_accounts.txt")
        if os.path.exists(target_file):
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    self.input_target_account.setPlainText(f.read())
            except:
                pass
        exclude_file = os.path.join(os.path.dirname(__file__), "exclude_emails.txt")
        if os.path.exists(exclude_file):
            try:
                with open(exclude_file, "r", encoding="utf-8") as f:
                    self.input_exclude_emails.setPlainText(f.read())
            except:
                pass

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange and self.isActiveWindow():
            self.load_txt_files()
        super().changeEvent(event)

    def load_config(self):
        self.load_txt_files()
                
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.full_config = json.load(f)
                    params = self.full_config.get("params", {})
                    
                    self.spin_past_hours.setValue(int(params.get("past_hours", 24)))
                    self.spin_no_response_threshold.setValue(int(params.get("no_response_threshold", 0)))
                    self.spin_max_emails.setValue(int(params.get("max_emails", 500)))
                    self.spin_retention_hours.setValue(int(params.get("retention_hours", 720)))
                    
                    lang = params.get("lang", "zh")
                    if lang == "en":
                        self.radio_en.setChecked(True)
                    else:
                        self.radio_zh.setChecked(True)
                        
                    self.lang = lang
            except Exception as e:
                QMessageBox.warning(self, tr("load_fail", self.lang), tr("load_fail_msg", self.lang).replace("{e}", str(e)))

    def save_config(self):
        try:
            target_file = os.path.join(os.path.dirname(__file__), "target_accounts.txt")
            with open(target_file, "w", encoding="utf-8") as tf:
                tf.write(self.input_target_account.toPlainText())
                
            exclude_file = os.path.join(os.path.dirname(__file__), "exclude_emails.txt")
            with open(exclude_file, "w", encoding="utf-8") as ef:
                ef.write(self.input_exclude_emails.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, tr("warning", self.lang), tr("save_fail_msg", self.lang).replace("{e}", str(e)))
            
        params = {
            "past_hours": self.spin_past_hours.value(),
            "no_response_threshold": self.spin_no_response_threshold.value(),
            "max_emails": self.spin_max_emails.value(),
            "retention_hours": self.spin_retention_hours.value(),
            "lang": "en" if self.radio_en.isChecked() else "zh"
        }
        self.full_config["params"] = params
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.full_config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, tr("save_success", self.lang), tr("save_success_msg", self.lang))
            self.close()
        except Exception as e:
            QMessageBox.critical(self, tr("error", self.lang), tr("save_fail_msg", self.lang).replace("{e}", str(e)))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec())
