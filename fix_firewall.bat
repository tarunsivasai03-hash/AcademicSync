@echo off
:: Right-click this file → "Run as administrator"
echo Adding firewall rules for AcademicSync...
netsh advfirewall firewall delete rule name="AcademicSync-5000" >nul 2>&1
netsh advfirewall firewall delete rule name="AcademicSync-3000" >nul 2>&1
netsh advfirewall firewall add rule name="AcademicSync-5000" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="AcademicSync-3000" dir=in action=allow protocol=TCP localport=3000
echo.
echo Done! Ports 3000 and 5000 are now open on the LAN.
echo Open this on your phone:  http://192.168.0.145:3000/login.html
echo.
pause
