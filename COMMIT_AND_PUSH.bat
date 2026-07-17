@echo off
REM ============================================================
REM  FundRadar — commit today's work and push to GitHub.
REM  Double-click this file. It will:
REM    1. clear any leftover git lock files
REM    2. stage all changes
REM    3. commit them with a message
REM    4. push to GitHub (origin)
REM  Safe to run more than once.
REM ============================================================
cd /d "%~dp0"

echo Clearing any leftover git locks...
del /f /q ".git\index.lock" 2>nul
del /f /q ".git\HEAD.lock" 2>nul

echo.
echo Staging changes...
git add -A

echo.
echo Committing...
git commit -m "Email verification (Resend, opt-in); chat bullet answers; demo login on boot; automation"

echo.
echo Pushing to GitHub...
git push

echo.
echo ============================================================
echo  Done. If you see errors above, copy them and send to Claude.
echo  If it says 'nothing to commit', everything is already saved.
echo ============================================================
pause
