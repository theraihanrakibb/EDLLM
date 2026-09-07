@echo off
REM One-click launcher: Ollama + web chat UI + local terminal.
REM All services run in THIS single window (no extra terminals).
title EDLLM - Local LLM Stack
set OLLAMA_MODELS=F:\tmp\Model
set OLLAMA_ORIGINS=*
set ROOT=F:\tmp\Model
set LOG=%ROOT%\logs
if not exist "%LOG%" mkdir "%LOG%"

taskkill /IM ollama.exe /F >nul 2>&1
timeout /t 1 >nul

echo Starting EDLLM services... logs saved to %LOG%
echo.

REM Each service runs in the background (start /b) inside this one window.
start /b cmd /c "title ollama  && ollama serve                                > "%LOG%\ollama.log"   2>&1"
start /b cmd /c "title webui   && cd /d %ROOT%\webui && python -m http.server 8000 > "%LOG%\webui.log"    2>&1"
start /b cmd /c "title term    && cd /d %ROOT%\webui && python terminal.py           > "%LOG%\terminal.log" 2>&1"
start /b cmd /c "title ws      && cd /d %ROOT%\webui && python wsserver.py           > "%LOG%\wsserver.log" 2>&1"

timeout /t 3 >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:8000 2>nul || start chrome http://localhost:8000 2>nul || start http://localhost:8000

echo.
echo  EDLLM is running in this single window:
echo    Chat:         http://localhost:8000
echo    Terminal API: http://localhost:8001
echo    Terminal WS:  ws://localhost:8002
echo    Ollama:       http://localhost:11434
echo    Logs:         %LOG%
echo.
echo  Close this window to stop everything.
echo.
cmd /k
