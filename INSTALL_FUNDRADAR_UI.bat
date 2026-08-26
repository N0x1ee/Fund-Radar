@echo off
cd /d "%~dp0"
echo ================================================
echo  FundRadar - install / upgrade dashboard add-ons
echo ================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" install_fundradar_ui.py
) else (
    python install_fundradar_ui.py
)
echo.
pause
