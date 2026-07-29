@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
REM Kept for backward compatibility; the frozen project uses unittest and no pytest dependency.
python scripts\test\run_tests.py
exit /b %errorlevel%
