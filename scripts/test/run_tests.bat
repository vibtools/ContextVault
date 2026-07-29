@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
python scripts\test\run_tests.py
exit /b %errorlevel%
