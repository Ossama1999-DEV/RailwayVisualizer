@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON=py -3"
%PYTHON% -c "import sys; assert sys.version_info.major == 3" >nul 2>&1
if errorlevel 1 (
  echo [ERREUR] Python 3 introuvable. Installer Python 3.
  pause
  exit /b 1
)
echo =========================================
echo        RAILWAY VISUALIZER v0.3
echo =========================================
echo Ouvrir dans VS Code - Simple Browser:
echo http://127.0.0.1:8767/
echo.
echo Laisser ce terminal ouvert. Ctrl+C pour arreter.
%PYTHON% serve.py 8767
if errorlevel 1 pause
