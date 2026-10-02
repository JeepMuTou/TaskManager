import os
import subprocess
import json
import sys
import threading
import queue
import time
from pathlib import Path
from typing import List, Dict, Any

class TaskManager:
    def __init__(self, tasks_dir: str, settings_store):
        self.tasks_dir = Path(tasks_dir)
        self.settings_store = settings_store
        self.running_processes = {}
        self.config_processes = {}
        
        self.task_queue = queue.Queue()
        self.queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.queue_thread.start()
        
        self.monitor_thread = threading.Thread(target=self._monitor_timeouts, daemon=True)
        self.monitor_thread.start()

    def _process_queue(self):
        while True:
            task_id, params = self.task_queue.get()
            
            # 如果不允许并行，我们需要等待当前所有正在运行的任务结束
            while not self.settings_store.allow_parallel_tasks:
                self._cleanup_dead_processes()
                if len(self.running_processes) > 0:
                    time.sleep(0.5)
                else:
                    break
                    
            self._do_execute(task_id, params)
            self.task_queue.task_done()

    def _cleanup_dead_processes(self):
        dead = []
        for tid, info in self.running_processes.items():
            if info["proc"].poll() is not None:
                dead.append(tid)
        for tid in dead:
            del self.running_processes[tid]

    def _monitor_timeouts(self):
        while True:
            try:
                now = time.time()
                killed = []
                # 遍历拷贝避免修改期间迭代冲突
                for tid, info in list(self.running_processes.items()):
                    if info["timeout_seconds"] > 0:
                        elapsed = now - info["start_time"]
                        if elapsed > info["timeout_seconds"]:
                            proc = info["proc"]
                            if proc.poll() is None:
                                try:
                                    proc.kill()
                                    print(f"Task {tid} killed due to timeout (> {info['timeout_seconds']}s)")
                                except Exception as e:
                                    print(f"Failed to kill timed-out task {tid}: {e}")
                            killed.append(tid)
                for tid in killed:
                    if tid in self.running_processes:
                        del self.running_processes[tid]
            except Exception as e:
                print(f"Error in timeout monitor: {e}")
            time.sleep(1)

    def scan_tasks(self) -> List[Dict[str, Any]]:
        tasks = []
        if not self.tasks_dir.exists():
            return tasks

        for item in self.tasks_dir.iterdir():
            if item.is_dir():
                metadata_file = item / "metadata.json"
                if metadata_file.exists():
                    metadata = self._get_task_metadata(metadata_file)
                    metadata['task_id'] = item.name
                    tasks.append(metadata)
                else:
                    tasks.append({
                        "task_id": item.name,
                        "name": item.name,
                        "description": "No description provided."
                    })
        return tasks

    def _get_task_metadata(self, metadata_file: Path) -> Dict[str, Any]:
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to read metadata {metadata_file}: {e}")
            return {"name": metadata_file.parent.name, "description": ""}

    def _get_python_exe(self):
        """获取用于执行插件的 Python 解释器路径，优先使用自带的绿色环境"""
        # 1. 确定程序根目录
        if getattr(sys, 'frozen', False):
            # 编译为 EXE 时的根目录
            root_dir = Path(sys.executable).parent
        else:
            # 源码运行时的根目录 (假定 task_manager.py 在 Source/app/core/ 下)
            root_dir = Path(__file__).parent.parent.parent
            
        # 2. 检查几种常见的自带 Python 环境路径
        possible_envs = [
            root_dir / "python_env" / "python.exe",            # 常见绿色版命名
            root_dir / "env" / "Scripts" / "python.exe",       # 标准 venv 命名1
            root_dir / ".venv" / "Scripts" / "python.exe"      # 标准 venv 命名2
        ]
        
        for env_exe in possible_envs:
            if env_exe.exists():
                print(f"Detected portable Python environment: {env_exe}")
                return str(env_exe)

        # 3. 如果没找到自带环境，则回退到系统环境
        if getattr(sys, 'frozen', False):
            return "python"
        return sys.executable

    def execute_task(self, task_id: str, params: dict = None):
        self.task_queue.put((task_id, params))
        print(f"Task {task_id} queued for execution.")

    def _do_execute(self, task_id: str, params: dict = None):
        task_dir = self.tasks_dir / task_id
        script_path = task_dir / "run.py"
        if not script_path.exists():
            print(f"Task script not found: {script_path}")
            return

        config_path = task_dir / "config.json"
        # 默认开启超时强杀，时间为10分钟
        timeout_seconds = 10 * 60
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    if cfg.get("timeout_enabled", True):
                        timeout_seconds = cfg.get("timeout_minutes", 10) * 60
                    else:
                        timeout_seconds = 0
            except:
                pass

        try:
            python_exe = self._get_python_exe()
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            proc = subprocess.Popen(
                [python_exe, "run.py"],
                cwd=str(task_dir),
                creationflags=creationflags
            )
            self.running_processes[task_id] = {
                "proc": proc,
                "start_time": time.time(),
                "timeout_seconds": timeout_seconds
            }
            print(f"Started task: {task_id}")
        except Exception as e:
            print(f"Failed to start task {task_id}: {e}")

    def is_task_running(self, task_id: str) -> bool:
        self._cleanup_dead_processes()
        if task_id in self.running_processes:
            return True
        
        # 检查是否在队列中排队
        for item in list(self.task_queue.queue):
            if item[0] == task_id:
                return True
                
        return False

    def kill_task(self, task_id: str):
        # 1. 如果还在队列中，踢出队列
        new_queue = queue.Queue()
        while not self.task_queue.empty():
            item = self.task_queue.get()
            if item[0] != task_id:
                new_queue.put(item)
        self.task_queue = new_queue

        # 2. 如果已经运行，直接杀死进程
        info = self.running_processes.get(task_id)
        if info is not None:
            proc = info["proc"]
            if proc.poll() is None:
                try:
                    proc.kill()
                    print(f"Killed task: {task_id}")
                except Exception as e:
                    print(f"Failed to kill task {task_id}: {e}")
            if task_id in self.running_processes:
                del self.running_processes[task_id]

    def open_task_config(self, task_id: str):
        task_dir = self.tasks_dir / task_id
        script_path = task_dir / "config_ui.py"
        if not script_path.exists():
            print(f"Config UI script not found: {script_path}")
            return

        try:
            python_exe = self._get_python_exe()
            proc = subprocess.Popen(
                [python_exe, "config_ui.py"],
                cwd=str(task_dir)
            )
            self.config_processes[task_id] = proc
            print(f"Opened config UI for task: {task_id}")
        except Exception as e:
            print(f"Failed to open config UI for task {task_id}: {e}")
