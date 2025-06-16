@echo off
echo === Message Communication Validation ===
echo.
echo This will run a comprehensive test of the messaging functionality.
echo.

REM Check if server is running
echo Checking if server is running on port 8000...
powershell -Command "(New-Object System.Net.Sockets.TcpClient).Connect('localhost', 8000)" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Server is not running on port 8000!
    echo.
    echo Please start the server first:
    echo   1. Open a new terminal
    echo   2. Navigate to: D:\Workspace\Python_Workspace\AIagent-dev\MAS
    echo   3. Run: cd server
    echo   4. Run: python main.py
    echo.
    pause
    exit /b 1
)

echo Server is running. Proceeding with tests...
echo.

cd /d "%~dp0"
cd ..

echo Installing required packages...
pip install aiohttp > nul 2>&1

echo.
echo Running validation tests...
echo.
python tests\validate_messaging.py

echo.
echo Validation completed.
pause
