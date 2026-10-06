@echo off
cd /d "%~dp0"
python -X utf8 -m cost_analyzer serve --port 8765
pause
