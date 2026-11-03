@echo off
rem Installs everything Ninja needs: Python 3.11, its packages, Ollama, the AI model, voice and shortcuts. Then opens Ninja.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
if errorlevel 1 (echo. & echo Install stopped. Read the message above, fix it, then run Install Ninja again. & pause & exit /b 1)
timeout /t 8
