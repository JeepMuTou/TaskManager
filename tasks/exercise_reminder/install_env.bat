@echo off
setlocal
chcp 65001 >nul

REM 1. Check PYTHON_EXE from environment or portable/venv
if not "%PYTHON_EXE%"=="" goto INSTALL
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

:INSTALL
cd /d "%~dp0"
echo ========================================================
echo Installing environment for exercise_reminder...
echo Using Python: %PYTHON_EXE%
echo ========================================================
echo.

if exist "requirements.txt" (
    "%PYTHON_EXE%" -m pip install -r requirements.txt
) else (
    "%PYTHON_EXE%" -m pip install PySide6
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
