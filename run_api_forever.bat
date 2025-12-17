@echo off
title AI Agent API Server (Port 8000)
:loop
echo [%DATE% %TIME%] Starting API Server...
uvicorn api:app --host 0.0.0.0 --port 8000
echo [%DATE% %TIME%] API crashed. Restarting in 5 seconds...
timeout /t 5
goto loop
