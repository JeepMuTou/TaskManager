import json
import os
import sys
from pathlib import Path

class SettingsStore:
    """管理全局设置 (语言、开机自启、最小化到托盘等)"""
    
    DEFAULT_SETTINGS = {
        "language": "zh",
        "auto_start": False,
        "minimize_to_tray": False,
        "allow_parallel_tasks": False
    }
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / "settings.json"
        self._settings = self._load()
    
    def _load(self) -> dict:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                # Merge with defaults to handle newly added keys
                merged = dict(self.DEFAULT_SETTINGS)
                merged.update(saved)
                return merged
            except Exception:
                pass
        return dict(self.DEFAULT_SETTINGS)
    
    def save(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def get(self, key: str, default=None):
        return self._settings.get(key, default)
    
    def set(self, key: str, value):
        self._settings[key] = value
    
    @property
    def language(self) -> str:
        return self._settings.get("language", "zh")
    
    @language.setter
    def language(self, val: str):
        self._settings["language"] = val
    
    @property
    def auto_start(self) -> bool:
        return self._settings.get("auto_start", False)
    
    @auto_start.setter
    def auto_start(self, val: bool):
        self._settings["auto_start"] = val
    
    @property
    def minimize_to_tray(self) -> bool:
        return self._settings.get("minimize_to_tray", False)
    
    @minimize_to_tray.setter
    def minimize_to_tray(self, val: bool):
        self._settings["minimize_to_tray"] = val

    @property
    def allow_parallel_tasks(self) -> bool:
        return self._settings.get("allow_parallel_tasks", False)
    
    @allow_parallel_tasks.setter
    def allow_parallel_tasks(self, val: bool):
        self._settings["allow_parallel_tasks"] = val

    # --- 开机自启 (Windows Registry) ---
    def apply_auto_start(self):
        """根据当前设置，写入或删除 Windows 注册表的开机自启项"""
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "TaskManager"
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            if self.auto_start:
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = f'"{sys.executable}" "{os.path.abspath("app/main.py")}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to set auto-start: {e}")
