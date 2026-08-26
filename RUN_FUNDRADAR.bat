@echo off
title FundRadar
cd /d "%~dp0"

echo ============================================================
echo   FundRadar - update the dashboard, then start the app
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

echo [1/2] Applying the latest dashboard design...
echo.
%PY% install_fundradar_ui.py
if errorlevel 1 (
    echo.
    echo ****************************************************
    echo  The update FAILED. The app was NOT started.
    echo  Copy the message above and send it to Claude.
    echo ****************************************************
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting the app...
echo.
echo    Open  http://127.0.0.1:8000/dashboard
echo    then press CTRL+SHIFT+R to force a fresh page.
echo.
echo    (Leave this window open while you use the app.
echo     Close it or press CTRL+C to stop the server.)
echo.

if exist "START_APP.bat" (
    call START_APP.bat
) else (
    %PY% -m uvicorn app.api.main:app --reload --port 8000
)

pause
