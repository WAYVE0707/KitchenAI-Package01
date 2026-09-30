@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 exit /b %errorlevel%
echo.
echo KitchenAI_Setup.exe is in dist\
endlocal
