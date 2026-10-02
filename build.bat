@echo off
echo Cleaning old builds...
rmdir /s /q build dist

pyinstaller --noconfirm --windowed --name TaskManager --add-data "app/assets/icon.jpg;app/assets" run_app.py

echo.
echo Build complete!
echo Your compiled program is in the 'dist\TaskManager' folder.
echo You can move the contents of that folder anywhere, but remember to put your 'tasks' and 'data' folders next to TaskManager.exe.
pause
