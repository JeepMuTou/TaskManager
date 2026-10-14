import subprocess
import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

class UpdateManager:
    @staticmethod
    def get_script_path() -> Path:
        base_dir = Path(__file__).resolve().parent.parent.parent
        script_path = base_dir / "UpdateScript" / "CheckUpdate.bat"
        return script_path
        
    @staticmethod
    def check_for_update():
        """
        Returns:
            True if an update is available.
            False if no update is available.
            None if an error occurred.
        """
        script_path = UpdateManager.get_script_path()
        if not script_path.exists():
            print(f"Update script not found at {script_path}")
            return None
            
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run([str(script_path), "check"], 
                                    capture_output=True, 
                                    creationflags=creationflags)
            if result.returncode == 1:
                return True
            elif result.returncode == 0:
                return False
            else:
                print(f"Check update script returned {result.returncode}")
                return None
        except Exception as e:
            print(f"Error checking update: {e}")
            return None

    @staticmethod
    def start_update():
        """Starts the update script and exits the main app."""
        script_path = UpdateManager.get_script_path()
        if not script_path.exists():
            print(f"Update script not found at {script_path}")
            return
            
        try:
            subprocess.Popen(["cmd.exe", "/c", str(script_path), "update"], 
                             cwd=str(script_path.parent),
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            # Kill the main app
            QApplication.quit()
        except Exception as e:
            print(f"Error starting update: {e}")
