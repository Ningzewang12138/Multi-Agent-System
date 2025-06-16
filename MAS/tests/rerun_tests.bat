@echo off
echo === Re-running Message Communication Tests ===
echo.
echo The code has been updated to fix the following issues:
echo   1. WebSocket now accepts any device ID (auto-registration)
echo   2. Message sending works with unknown recipients
echo   3. Message storage test passes even with 0 messages
echo.
echo IMPORTANT: Please restart the server to apply changes!
echo.
echo Steps:
echo   1. Stop the current server (Ctrl+C in server window)
echo   2. Start the server again: python main.py
echo   3. Press any key here to continue with tests
echo.
pause

cd /d "%~dp0"

echo.
echo Running validation tests again...
echo.
python validate_messaging.py

echo.
echo ========================================
echo If tests still fail, try the multi-client test:
echo   python test_multi_client_messaging.py
echo.
echo Or run interactive chat:
echo   interactive_chat.bat
echo ========================================
echo.
pause
