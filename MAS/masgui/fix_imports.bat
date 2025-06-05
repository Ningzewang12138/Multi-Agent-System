@echo off
echo Fixing package imports in Flutter project...

set OLD_PACKAGE=ollama_app
set NEW_PACKAGE=masgui

:: List of files to fix
set FILES=lib\screen_voice.dart lib\worker\setter.dart lib\worker\update.dart lib\settings\behavior.dart lib\settings\interface.dart lib\settings\voice.dart lib\settings\export.dart lib\settings\about.dart

:: Fix each file
for %%f in (%FILES%) do (
    echo Fixing %%f...
    powershell -Command "(Get-Content '%%f' -Raw) -replace 'package:%OLD_PACKAGE%/', 'package:%NEW_PACKAGE%/' | Set-Content '%%f' -NoNewline"
)

echo Done!
