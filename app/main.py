import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    sys.path.append(sys._MEIPASS)
else:
    sys.path.append(str(Path(__file__).parent.parent))
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.core.task_manager import TaskManager
from app.core.scheduler import SchedulerManager
from app.utils.config_store import ConfigStore
from app.utils.settings_store import SettingsStore

def main():
    app = QApplication(sys.argv)
    
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent
        
    tasks_dir = base_dir / "tasks"
    data_dir = base_dir / "data"
    
    tasks_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    settings_store = SettingsStore(str(data_dir))
    config_store = ConfigStore(str(tasks_dir))
    task_manager = TaskManager(str(tasks_dir), settings_store)
    
    scheduler_manager = SchedulerManager(task_executor=task_manager.execute_task)
    
    window = MainWindow(task_manager, scheduler_manager, config_store, settings_store)
    window.show()
    
    exit_code = app.exec()
    scheduler_manager.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
