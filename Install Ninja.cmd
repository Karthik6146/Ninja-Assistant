@echo off
rem Installs Ninja: Python 3.11 if missing, the app, shortcuts, then opens the setup wizard.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
if errorlevel 1 (echo. & echo Install stopped. Read the message above, fix it, then run Install Ninja again. & pause & exit /b 1)
timeout /t 8
