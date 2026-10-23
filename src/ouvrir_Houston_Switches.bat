@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_CMD=python"
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
if "%PYTHON_CMD%"=="python" (
    python -c "import sys" >nul 2>&1
    if errorlevel 1 (
       echo [ERREUR] Python 3 n'est pas installe ou pas dans le PATH.
       pause
       exit /b 1
    )
)
set "CHOIX=%~1"
if "%CHOIX%"=="" (
    echo ============================================
    echo   HOUSTON METRORAIL - SWITCH VIEWER AUTO
    echo ============================================
    echo  1 - Red Line
    echo  2 - Green Line
    echo  3 - Les deux lignes
    echo.
    set /p "CHOIX=Choisis 1, 2 ou 3 puis Entree : "
)
if "%CHOIX%"=="1" set "LINE=red"
if "%CHOIX%"=="2" set "LINE=green"
if "%CHOIX%"=="3" set "LINE=both"
if not defined LINE (
    echo [ERREUR] Choix invalide. Utilise 1, 2 ou 3.
    pause
    exit /b 1
)
echo.
echo [1/2] Recuperation automatique des switches depuis OpenStreetMap...
%PYTHON_CMD% update_switches.py
if errorlevel 1 (
    echo.
    echo [ATTENTION] Un telechargement a echoue. Les anciens CSV sont conserves si disponibles.
)
echo.
echo [2/2] Lancement de la carte locale...
echo Dans VS Code : Ctrl+Shift+P puis Simple Browser: Show
echo Adresse : http://127.0.0.1:8767/houston_switches_map.html?line=%LINE%
echo.
echo Garde ce terminal ouvert. Ctrl+C pour arreter.
%PYTHON_CMD% serve.py 8767
if errorlevel 1 pause
