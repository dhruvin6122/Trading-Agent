@echo off
title AI Trading Agent - 24/7 Monitor
:loop
echo [%DATE% %TIME%] Starting Trading Agent...
python main.py
echo [%DATE% %TIME%] Agent crashed or stopped. Restarting in 10 seconds...
timeout /t 10
goto loop
