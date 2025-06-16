@echo off
echo === Interactive Chat Client ===
echo.
echo This will start an interactive chat client.
echo Make sure the server is running on port 8000.
echo.
pause

cd /d "%~dp0"
cd ..

echo Installing required packages...
pip install aiohttp > nul 2>&1

echo.
echo Starting interactive chat client...
python tests\test_messaging.py chat
