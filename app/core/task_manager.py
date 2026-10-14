import os
import subprocess
import json
import sys
import threading
import queue
import time
from pathlib import Path
from typing import List, Dict, Any, Set

RUN_BAT_TEMPLATE = """@echo off
setlocal
chcp 65001 >nul

REM 1. Check PYTHON_EXE from environment
if not "%PYTHON_EXE%"=="" goto RUN

REM 2. Check portable env or virtual env
set "ROOT_DIR=%~dp0..\\.."
if exist "%ROOT_DIR%\\python_env\\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\\python_env\\python.exe"
) else if exist "%ROOT_DIR%\\env\\Scripts\\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\\env\\Scripts\\python.exe"
) else if exist "%ROOT_DIR%\\.venv\\Scripts\\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\\.venv\\Scripts\\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:RUN
cd /d "%~dp0"
"%PYTHON_EXE%" run.py %*
exit /b %ERRORLEVEL%
"""

def _get_process_children(parent_pid: int) -> List[int]:
    """获取指定 PID 的所有子代/后代进程 PID (Windows Toolhelp32Snapshot)"""
    if sys.platform != "win32" or parent_pid <= 0:
        return []
    children = []
    try:
        import ctypes
        from ctypes import wintypes
        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_char * 260)
            ]
        k32 = ctypes.windll.kernel32
        hSnapshot = k32.CreateToolhelp32Snapshot(0x00000002, 0)
        if hSnapshot in (-1, 0):
            return []
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        all_procs = []
        if k32.Process32First(hSnapshot, ctypes.byref(pe)):
            while True:
                all_procs.append((pe.th32ProcessID, pe.th32ParentProcessID))
                if not k32.Process32Next(hSnapshot, ctypes.byref(pe)):
                    break
        k32.CloseHandle(hSnapshot)

        queue_pids = [parent_pid]
        while queue_pids:
            curr = queue_pids.pop(0)
            for pid, ppid in all_procs:
                if ppid == curr and pid not in children:
                    children.append(pid)
                    queue_pids.append(pid)
    except Exception:
        pass
    return children

def _is_pid_alive(pid: int) -> bool:
    """检查 PID 对应的进程是否仍在运行"""
    if sys.platform != "win32" or pid <= 0:
        return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        SYNCHRONIZE = 0x00100000
        handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        STILL_ACTIVE = 259
        alive = False
        if k32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            alive = (exit_code.value == STILL_ACTIVE)
        k32.CloseHandle(handle)
        return alive
    except Exception:
        return False

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

    def _is_task_running_internal(self, info: dict) -> bool:
        proc = info.get("proc")
        pid = info.get("pid", proc.pid if proc else None)
        child_pids = info.setdefault("child_pids", set())

        if pid is not None:
            # 如果主进程 (cmd.exe) 仍在运行
            if proc and proc.poll() is None:
                # 动态刷新追踪到的子进程 (如 cmd 唤起的 python.exe)
                for cpid in _get_process_children(pid):
                    child_pids.add(cpid)
                return True

            # 如果主进程已退出，检查是否有残留未退出的子进程 (如后台 python.exe)
            alive_children = set()
            for cpid in list(child_pids):
                if _is_pid_alive(cpid):
                    alive_children.add(cpid)
            info["child_pids"] = alive_children
            return len(alive_children) > 0

        return False

    def _kill_task_process(self, info: dict):
        proc = info.get("proc")
        pid = info.get("pid", proc.pid if proc else None)
        child_pids = info.setdefault("child_pids", set())

        if pid is not None and sys.platform == "win32":
            # 强杀前刷新子进程列表
            for cpid in _get_process_children(pid):
                child_pids.add(cpid)

            # 1. 在 Windows 上优先使用 taskkill /F /T /PID 递归整棵进程树
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                print(f"taskkill failed on PID {pid}: {e}")

        # 2. 如果 proc 仍未退出，执行 proc.kill()
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

        # 3. 针对记录过的每一个子进程 PID 进行二次确认与强杀，杜绝孤儿进程
        if sys.platform == "win32":
            import ctypes
            k32 = ctypes.windll.kernel32
            PROCESS_TERMINATE = 0x0001
            for cpid in list(child_pids):
                if _is_pid_alive(cpid):
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(cpid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    except Exception:
                        pass
                    try:
                        h = k32.OpenProcess(PROCESS_TERMINATE, False, cpid)
                        if h:
                            k32.TerminateProcess(h, 1)
                            k32.CloseHandle(h)
                    except Exception:
                        pass

        info["child_pids"] = set()

    def _cleanup_dead_processes(self):
        dead = []
        for tid, info in list(self.running_processes.items()):
            if not self._is_task_running_internal(info):
                dead.append(tid)
        for tid in dead:
            del self.running_processes[tid]

    def _monitor_timeouts(self):
        while True:
            try:
                now = time.time()
                killed = []
                for tid, info in list(self.running_processes.items()):
                    if info["timeout_seconds"] > 0:
                        elapsed = now - info["start_time"]
                        if elapsed > info["timeout_seconds"]:
                            if self._is_task_running_internal(info):
                                try:
                                    self._kill_task_process(info)
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
        bat_path = task_dir / "run.bat"
        py_path = task_dir / "run.py"

        # 如果任务目录下没有 run.bat，但存在 run.py，则自动生成标准 run.bat
        if not bat_path.exists():
            if py_path.exists():
                try:
                    with open(bat_path, "w", encoding="utf-8") as f:
                        f.write(RUN_BAT_TEMPLATE)
                    print(f"Auto-generated run.bat for task: {task_id}")
                except Exception as e:
                    print(f"Failed to auto-generate run.bat for task {task_id}: {e}")
            else:
                print(f"Task entry script not found: {bat_path} / {py_path}")
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
            env = os.environ.copy()
            env["PYTHON_EXE"] = python_exe

            if bat_path.exists():
                cmd = ["cmd.exe", "/c", str(bat_path)]
            else:
                cmd = [python_exe, "run.py"]

            proc = subprocess.Popen(
                cmd,
                cwd=str(task_dir),
                creationflags=creationflags,
                env=env
            )
            self.running_processes[task_id] = {
                "proc": proc,
                "pid": proc.pid,
                "child_pids": set(),
                "start_time": time.time(),
                "timeout_seconds": timeout_seconds
            }
            print(f"Started task: {task_id} via bat (PID: {proc.pid})")
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

        # 2. 如果已经运行，直接杀死整棵进程树与所有派生子进程
        info = self.running_processes.get(task_id)
        if info is not None:
            self._kill_task_process(info)
            print(f"Killed task: {task_id}")
            if task_id in self.running_processes:
                del self.running_processes[task_id]

    def open_task_config(self, task_id: str):
        task_dir = self.tasks_dir / task_id
        bat_path = task_dir / "config_ui.bat"
        script_path = task_dir / "config_ui.py"

        python_exe = self._get_python_exe()
        env = os.environ.copy()
        env["PYTHON_EXE"] = python_exe

        if bat_path.exists():
            try:
                proc = subprocess.Popen(
                    ["cmd.exe", "/c", str(bat_path)],
                    cwd=str(task_dir),
                    env=env
                )
                self.config_processes[task_id] = proc
                print(f"Opened config UI via bat for task: {task_id}")
                return
            except Exception as e:
                print(f"Failed to open config UI via bat for task {task_id}: {e}")

        if not script_path.exists():
            print(f"Config UI script not found: {script_path}")
            return

        try:
            proc = subprocess.Popen(
                [python_exe, "config_ui.py"],
                cwd=str(task_dir),
                env=env
            )
            self.config_processes[task_id] = proc
            print(f"Opened config UI for task: {task_id}")
        except Exception as e:
            print(f"Failed to open config UI for task {task_id}: {e}")
