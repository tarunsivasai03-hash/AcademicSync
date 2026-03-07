@echo off
cd /d "%~dp0academic_system"
"%~dp0.venv\Scripts\python.exe" -m http.server 3000 --bind 0.0.0.0
