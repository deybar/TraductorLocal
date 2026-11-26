@echo off
chcp 65001 >nul
title Traductor Local Offline (Consola)

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"

echo =======================================================
echo   TRADUCTOR LOCAL OFFLINE - MODO CONSOLA / DEBUG
echo =======================================================
echo.

set "PYTHON_EXE=C:\Users\%USERNAME%\.audio_translator_venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=C:\Users\%USERNAME%\.local_translator_venv\Scripts\python.exe"
)
if not exist "%PYTHON_EXE%" (
    if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" "%APP_DIR%\main.py"

echo.
echo La aplicacion ha finalizado.
pause >nul
