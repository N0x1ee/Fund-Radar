@echo off
REM Double-click to start FundRadar. Leave this window open while using the app.
cd /d "%~dp0"
echo Starting FundRadar...
echo.
echo When you see "Application startup complete", open your browser to:
echo     http://127.0.0.1:8000
echo.
echo To STOP the app: close this window (or press Ctrl+C).
echo ---------------------------------------------------------------
echo.
".venv\Scripts\python.exe" -m uvicorn app.api.main:app --reload
echo.
echo (The app has stopped.)
pause
