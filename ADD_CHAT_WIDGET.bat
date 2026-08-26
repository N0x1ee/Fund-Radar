@echo off
REM ---------------------------------------------------------------
REM  This is the OLD installer. It now just runs the current one,
REM  so double-clicking either file does the right thing.
REM ---------------------------------------------------------------
cd /d "%~dp0"
echo This installer was replaced. Running INSTALL_FUNDRADAR_UI instead...
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" install_fundradar_ui.py
) else (
    python install_fundradar_ui.py
)
echo.
pause
