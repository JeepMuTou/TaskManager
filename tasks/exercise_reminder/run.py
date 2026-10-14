import sys
import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

def load_config():
    config_path = Path(__file__).resolve().parent / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return {}

class ExerciseReminderWindow(QWidget):
    def __init__(self, title="运动提醒", content="该去运动啦！站起来活动一下身体，伸展筋骨，保护颈椎与视力！", 
                 sound=True, snooze=True, auto_close_seconds=0, is_preview=False, parent=None):
        super().__init__(parent)
        self.title_text = title if title else "运动提醒"
        self.content_text = content if content else "该去运动啦！站起来活动一下身体，伸展筋骨，保护颈椎与视力！"
        self.sound = sound
        self.snooze = snooze
        self.auto_close_seconds = auto_close_seconds
        self.is_preview = is_preview
        self.remaining_seconds = auto_close_seconds
        self.countdown_timer = None
        
        self.init_ui()

    def init_ui(self):
        # 置顶窗口设置
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle(self.title_text)
        self.setMinimumWidth(450)
        self.setMinimumHeight(260)
        self.resize(480, 280)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 头部区域：带健康/运动色彩的徽章和标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel("🏃‍♂️")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 26px;
                background-color: #dcfce7;
                border: 2px solid #86efac;
                border-radius: 24px;
            }
        """)
        header_layout.addWidget(icon_label)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(3)
        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a;")
        
        sub_title = QLabel("关爱健康 · 活力运动")
        sub_title.setStyleSheet("font-size: 12px; color: #10b981; font-weight: 500;")
        
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(sub_title)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # 内容卡片区域
        content_card = QFrame()
        content_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(8)

        self.lbl_content = QLabel(self.content_text)
        self.lbl_content.setWordWrap(True)
        self.lbl_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_content.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.6;
                color: #334155;
                background-color: transparent;
                border: none;
            }
        """)
        content_layout.addWidget(self.lbl_content)

        # 倒计时显示
        if self.auto_close_seconds > 0:
            self.lbl_countdown = QLabel(f"⏱️ 弹窗将在 {self.auto_close_seconds} 秒后自动关闭")
            self.lbl_countdown.setStyleSheet("font-size: 12px; color: #94a3b8; background-color: transparent; border: none;")
            content_layout.addWidget(self.lbl_countdown)
            
            self.countdown_timer = QTimer(self)
            self.countdown_timer.setInterval(1000)
            self.countdown_timer.timeout.connect(self._on_countdown_tick)
            self.countdown_timer.start()

        main_layout.addWidget(content_card, 1)

        # 底部按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        if self.snooze:
            self.btn_snooze = QPushButton("⏰ 稍后提醒 (5分钟)")
            self.btn_snooze.setCursor(Qt.PointingHandCursor)
            self.btn_snooze.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #475569;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                    border-color: #94a3b8;
                    color: #1e293b;
                }
                QPushButton:pressed {
                    background-color: #cbd5e1;
                }
            """)
            self.btn_snooze.clicked.connect(self._on_snooze_clicked)
            btn_layout.addWidget(self.btn_snooze)

        self.btn_confirm = QPushButton("💪 我知道了，去运动！")
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
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
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)
        btn_layout.addWidget(self.btn_confirm)

        main_layout.addLayout(btn_layout)

        # 居中显示在屏幕中央
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2 + screen_geo.x()
            y = (screen_geo.height() - self.height()) // 2 + screen_geo.y()
            self.move(x, y)

    def bring_to_front(self):
        """确保窗口置顶并成为当前活动焦点窗口"""
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.show()
        self.raise_()
        self.activateWindow()

        # Windows 专有前置置顶强化
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                # HWND_TOPMOST = -1, SWP_NOMOVE = 0x0002, SWP_NOSIZE = 0x0001, SWP_SHOWWINDOW = 0x0040
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

    def play_sound(self):
        """播放提醒音"""
        if self.sound:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _on_confirm_clicked(self):
        if self.countdown_timer:
            self.countdown_timer.stop()
        self.close()

    def _on_snooze_clicked(self):
        if self.countdown_timer:
            self.countdown_timer.stop()

        if self.is_preview:
            QMessageBox.information(
                self, 
                "预览提示", 
                "当前处于预览模式。\n在实际执行中，点击此按钮将隐藏弹窗并在 5 分钟后再次弹出置顶提醒。"
            )
            self.close()
            return

        self.hide()
        # 5分钟 (300秒) 后重新唤醒
        QTimer.singleShot(300 * 1000, self._on_snooze_timeout)

    def _on_snooze_timeout(self):
        self.bring_to_front()
        self.play_sound()
        if self.auto_close_seconds > 0:
            self.remaining_seconds = self.auto_close_seconds
            if self.countdown_timer:
                self.countdown_timer.start()

    def _on_countdown_tick(self):
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            if self.countdown_timer:
                self.countdown_timer.stop()
            self.close()
        else:
            if hasattr(self, 'lbl_countdown'):
                self.lbl_countdown.setText(f"⏱️ 弹窗将在 {self.remaining_seconds} 秒后自动关闭")

    def closeEvent(self, event):
        if self.countdown_timer:
            self.countdown_timer.stop()
        event.accept()
        if not self.is_preview:
            QApplication.quit()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ExerciseReminder")

    config = load_config()
    params = config.get("params", {})

    title = params.get("title", "运动提醒")
    content = params.get("content", "该去运动啦！站起来活动一下身体，伸展筋骨，保护颈椎与视力！")
    sound = params.get("sound", True)
    snooze = params.get("snooze", True)
    auto_close = int(params.get("auto_close_seconds", 0))

    is_preview = "--preview" in sys.argv

    window = ExerciseReminderWindow(
        title=title,
        content=content,
        sound=sound,
        snooze=snooze,
        auto_close_seconds=auto_close,
        is_preview=is_preview
    )
    window.bring_to_front()
    window.play_sound()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
