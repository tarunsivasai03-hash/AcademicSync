@echo off
title AcademicSync Launcher
echo.
echo  ================================================
echo   AcademicSync - Starting all servers...
echo  ================================================
echo.

:: --- Detect LAN IP (first non-loopback IPv4 address) ---
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do (
    set "LAN_IP=%%A"
    goto :gotip
)
:gotip
:: Strip leading space from the IP
set "LAN_IP=%LAN_IP: =%"

:: --- Start combined server (Flask serves both API and frontend) ---
echo  Starting AcademicSync on http://localhost:5000 ...
start "AcademicSync" cmd /k "cd /d %~dp0backend && %~dp0.venv\Scripts\python.exe run.py"

:: Wait for Flask to initialise
timeout /t 3 /nobreak >nul

:: --- Open browser ---
echo  Opening browser...
start http://localhost:5000/login.html

echo.
echo  ================================================
echo   App       : http://localhost:5000
echo   API health: http://localhost:5000/api/health
echo.
echo   *** LAN / Wi-Fi (open on your phone) ***
echo   App       : http://%LAN_IP%:5000/login.html
echo  ================================================
echo.