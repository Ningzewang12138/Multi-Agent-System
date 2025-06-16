@echo off
echo === Testing Message Communication ===
echo.
echo This test will verify the client messaging functionality.
echo Make sure the server is running on port 8000.
echo.
pause

cd /d "%~dp0"
cd ..

echo Installing required packages...
pip install aiohttp > nul 2>&1

echo.
echo Running message communication test...
python tests\test_messaging.py

echo.
echo Test completed. Press any key to exit...
pause > nul
