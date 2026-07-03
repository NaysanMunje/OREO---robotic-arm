@echo off
cd /d "%~dp0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8010.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
start "Model Viewer" /MIN .\.venv\Scripts\python.exe model_viewer\main.py
timeout /t 2 /nobreak >nul
start http://localhost:8010
