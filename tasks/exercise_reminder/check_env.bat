@echo off
setlocal
chcp 65001 >nul

REM 1. Check PYTHON_EXE from environment or portable/venv
if not "%PYTHON_EXE%"=="" goto CHECK
set "ROOT_DIR=%~dp0..\.."
if exist "%ROOT_DIR%\python_env\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\python_env\python.exe"
) else if exist "%ROOT_DIR%\env\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\env\Scripts\python.exe"
) else if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
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

REM Check required modules
"%PYTHON_EXE%" -c "import PySide6" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Missing required Python libraries: PySide6
    exit /b 1
)

echo [OK] Environment is ready.
exit /b 0
