@echo off
echo === Message Test with Timeout Control ===
echo.
echo This test includes timeout controls to prevent hanging.
echo Each operation will timeout after 5 seconds.
echo.
echo Testing message API endpoints...
echo.

cd /d "%~dp0"
python test_with_timeout.py
