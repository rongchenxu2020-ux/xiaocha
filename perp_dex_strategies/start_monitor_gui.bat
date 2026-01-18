@echo off
cd /d "%~dp0"
echo Starting Order Flow Monitor GUI...
py booking\monitor_bots_gui.py
if errorlevel 1 (
    echo Trying with python command...
    python booking\monitor_bots_gui.py
)
pause
