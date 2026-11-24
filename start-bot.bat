@echo off
title Dinesh K - Portfolio Telegram Bot
cd /d "%~dp0"
echo =======================================================
echo Starting Dinesh K Portfolio Telegram Bot...
echo =======================================================
python bot.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot stopped with an error or TELEGRAM_BOT_TOKEN is missing.
    pause
)
