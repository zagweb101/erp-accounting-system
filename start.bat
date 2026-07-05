@echo off
chcp 65001 >nul
title ERP Accounting System
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo ❌ Error starting application. Check if Python and requirements are installed.
    pause
)
