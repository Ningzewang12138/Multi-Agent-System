@echo off
echo === Simple Message Test ===
echo.
echo This test will check basic messaging functionality.
echo.
echo IMPORTANT: The server needs to be restarted for the message routes to work!
echo.
echo If you see 404 errors, please:
echo   1. Stop the server (Ctrl+C)
echo   2. Start it again: python main.py
echo.
pause

cd /d "%~dp0"

echo.
echo Running simple message test...
echo.
python simple_message_test.py

echo.
pause
