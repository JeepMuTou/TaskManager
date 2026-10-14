@echo off
setlocal
chcp 65001 >nul

REM 1. Check PYTHON_EXE from environment
if not "%PYTHON_EXE%"=="" goto RUN

REM 2. Check portable env or virtual env
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

:RUN
cd /d "%~dp0"
"%PYTHON_EXE%" config_ui.py %*
exit /b %ERRORLEVEL%
