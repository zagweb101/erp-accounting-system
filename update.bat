@echo off
chcp 65001 >nul
title Update ERP Accounting System
cd /d "%~dp0"
echo 🔄 Updating from GitHub...
git pull
echo ✅ Updated!
pause
