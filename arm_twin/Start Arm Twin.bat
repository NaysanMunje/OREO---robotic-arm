@echo off
cd /d "%~dp0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
start "Arm Twin" /MIN .\.venv\Scripts\python.exe main.py
timeout /t 3 /nobreak >nul
start http://localhost:8000
