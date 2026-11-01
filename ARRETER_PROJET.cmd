@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1" -WithMongo
echo.
echo Les donnees enregistrees sont conservees.
pause
