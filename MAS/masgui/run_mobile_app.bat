@echo off
echo Starting Multi-Agent System Mobile App...
echo.

echo Checking Flutter installation...
flutter --version
echo.

echo Getting dependencies...
flutter pub get
echo.

echo Available devices:
flutter devices
echo.

echo Starting the app...
flutter run

pause
