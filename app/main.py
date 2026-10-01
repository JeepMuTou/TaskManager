import sys
import os
from pathlib import Path

# 将 Source 目录添加到 sys.path 以便能够正确导入 app 模块
sys.path.append(str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.core.task_manager import TaskManager
from app.core.scheduler import SchedulerManager
from app.utils.config_store import ConfigStore

def main():
    app = QApplication(sys.argv)
    
    base_dir = Path(__file__).parent.parent
    tasks_dir = base_dir / "tasks"
    data_dir = base_dir / "data"
    
    # 初始化核心组件
    config_store = ConfigStore(str(tasks_dir))
    task_manager = TaskManager(str(tasks_dir))
    
    # 传递 task_manager 的执行函数给调度器
    scheduler_manager = SchedulerManager(task_executor=task_manager.execute_task)
    
    # 初始化并显示主窗口
    window = MainWindow(task_manager, scheduler_manager, config_store)
    window.show()
    
    # 启动事件循环
    exit_code = app.exec()
    
    # 程序退出时清理资源
    scheduler_manager.shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
