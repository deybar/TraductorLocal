@echo off
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"

start "" wscript.exe "%APP_DIR%\iniciar.vbs"
exit
