@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_demo.ps1"
if errorlevel 1 (
  echo Une erreur est survenue. Copiez le message ci-dessus.
  pause
  exit /b 1
)
:menu
echo.
echo FROID CONNECT - COMMANDES DU TABLEAU DE BORD
echo Donnees simulees. Ces touches ne commandent pas Wokwi.
echo 1 = Normal 5 C      2 = Chaud 12 C      3 = Froid 0 C
echo 4 = Cycle auto     5 = Pause envois    6 = Reprendre
echo 7 = Arreter les donnees et fermer ce menu
echo Mot de passe : .runtime\acces-local.txt
choice /c 1234567 /n /m "Votre choix : "
set "demoChoice=%errorlevel%"
if "%demoChoice%"=="7" (
  .venv\Scripts\python.exe scripts\presentation.py --command stop
  exit /b
)
if "%demoChoice%"=="6" .venv\Scripts\python.exe scripts\presentation.py --command resume
if "%demoChoice%"=="5" .venv\Scripts\python.exe scripts\presentation.py --command pause
if "%demoChoice%"=="4" .venv\Scripts\python.exe scripts\presentation.py --command auto
if "%demoChoice%"=="3" .venv\Scripts\python.exe scripts\presentation.py --command low
if "%demoChoice%"=="2" .venv\Scripts\python.exe scripts\presentation.py --command hot
if "%demoChoice%"=="1" .venv\Scripts\python.exe scripts\presentation.py --command normal
goto menu
