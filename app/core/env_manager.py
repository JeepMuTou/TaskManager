import os
import sys
import subprocess
import threading
from pathlib import Path
from typing import Dict, Tuple, List

CHECK_ENV_BAT_TEMPLATE = """@echo off
setlocal
chcp 65001 >nul

REM 1. Check PYTHON_EXE from environment or portable/venv
if not "%PYTHON_EXE%"=="" goto CHECK
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

:CHECK
REM Check if python is available
"%PYTHON_EXE%" --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python environment not found: %PYTHON_EXE%
    exit /b 1
)

if exist "requirements.txt" (
    "%PYTHON_EXE%" -m pip --version >nul 2>&1
)

echo [OK] Environment is ready.
exit /b 0
"""

INSTALL_ENV_BAT_TEMPLATE = """@echo off
setlocal
chcp 65001 >nul

REM 1. Check PYTHON_EXE from environment or portable/venv
if not "%PYTHON_EXE%"=="" goto INSTALL
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

:INSTALL
cd /d "%~dp0"
echo ========================================================
echo Installing environment for task...
echo Using Python: %PYTHON_EXE%
echo ========================================================
echo.

if exist "requirements.txt" (
    "%PYTHON_EXE%" -m pip install -r requirements.txt
) else (
    echo No requirements.txt found.
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Installation failed with exit code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUCCESS] Environment installed successfully!
timeout /t 3
exit /b 0
"""

class EnvManager:
    def __init__(self, tasks_dir: str):
        self.tasks_dir = Path(tasks_dir)
        if getattr(sys, 'frozen', False):
            self.root_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parent.parent.parent
        self.python_env_dir = self.root_dir / "python_env"

    def get_current_python(self) -> str:
        possible_envs = [
            self.root_dir / "python_env" / "python.exe",
            self.root_dir / "env" / "Scripts" / "python.exe",
            self.root_dir / ".venv" / "Scripts" / "python.exe"
        ]
        for env_exe in possible_envs:
            if env_exe.exists():
                return str(env_exe)
        if getattr(sys, 'frozen', False):
            return "python"
        return sys.executable

    def ensure_task_scripts(self, task_id: str):
        task_dir = self.tasks_dir / task_id
        if not task_dir.is_dir():
            return
        check_bat = task_dir / "check_env.bat"
        install_bat = task_dir / "install_env.bat"

        # 如果任务目录下没有 check_env.bat，但存在 run.py，自动生成模板
        if not check_bat.exists() and (task_dir / "run.py").exists():
            try:
                with open(check_bat, 'w', encoding='utf-8') as f:
                    f.write(CHECK_ENV_BAT_TEMPLATE)
            except Exception as e:
                print(f"Failed to auto-generate check_env.bat for {task_id}: {e}")

        # 如果任务目录下没有 install_env.bat，但存在 run.py，自动生成模板
        if not install_bat.exists() and (task_dir / "run.py").exists():
            try:
                with open(install_bat, 'w', encoding='utf-8') as f:
                    f.write(INSTALL_ENV_BAT_TEMPLATE)
            except Exception as e:
                print(f"Failed to auto-generate install_env.bat for {task_id}: {e}")

    def check_task_env(self, task_id: str) -> Tuple[bool, str]:
        self.ensure_task_scripts(task_id)
        task_dir = self.tasks_dir / task_id
        check_bat = task_dir / "check_env.bat"
        if not check_bat.exists():
            return True, "No check_env.bat (Skipped)"

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            env = os.environ.copy()
            env["PYTHON_EXE"] = self.get_current_python()
            res = subprocess.run(
                ["cmd.exe", "/c", str(check_bat)],
                cwd=str(task_dir),
                capture_output=True,
                text=True,
                creationflags=creationflags,
                env=env
            )
            out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            return (res.returncode == 0), out.strip()
        except Exception as e:
            return False, str(e)

    def install_task_env(self, task_id: str) -> bool:
        self.ensure_task_scripts(task_id)
        task_dir = self.tasks_dir / task_id
        install_bat = task_dir / "install_env.bat"
        if not install_bat.exists():
            print(f"install_env.bat not found in {task_dir}")
            return False

        try:
            creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            env = os.environ.copy()
            env["PYTHON_EXE"] = self.get_current_python()
            subprocess.Popen(
                ["cmd.exe", "/c", str(install_bat)],
                cwd=str(task_dir),
                creationflags=creationflags,
                env=env
            )
            return True
        except Exception as e:
            print(f"Failed to run install_env.bat for {task_id}: {e}")
            return False

    def check_all_tasks(self) -> Dict[str, Tuple[bool, str]]:
        results = {}
        if not self.tasks_dir.exists():
            return results
        for item in self.tasks_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                results[item.name] = self.check_task_env(item.name)
        return results

    def install_tasks_env(self, task_ids: List[str]):
        for tid in task_ids:
            self.install_task_env(tid)
