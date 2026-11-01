@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" -Tunnel
if errorlevel 1 (
  echo.
  echo Le lancement a rencontre une erreur. Copiez le message ci-dessus.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8000"
echo.
echo Mot de passe : .runtime\acces-local.txt
echo Guide : docs\DEMARRAGE_RAPIDE.md
echo Vous pouvez fermer cette fenetre. Les services restent actifs.
pause
