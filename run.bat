@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 src\app.py
) else (
    python src\app.py
)

set "EXIT_CODE=%errorlevel%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo ContextVault exited with code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
