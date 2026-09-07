@echo off
title EDLLM - Local LLM Stack
setlocal
set OLLAMA_MODELS=F:\tmp\Model
set OLLAMA_ORIGINS=*
set ROOT=F:\tmp\Model
set LOG=%ROOT%\logs
if not exist "%LOG%" mkdir "%LOG%"

echo Stopping any previous instance...
call :killports
timeout /t 1 >nul

echo Starting EDLLM services... logs saved to %LOG%
echo.

REM Each service runs in the background (start /b) inside THIS single window.
start /b cmd /c "cd /d %ROOT%\webui && ollama serve                                 > "%LOG%\ollama.log"   2>&1"
start /b cmd /c "cd /d %ROOT%\webui && python -m http.server 8000                   > "%LOG%\webui.log"    2>&1"
start /b cmd /c "cd /d %ROOT%\webui && python terminal.py                           > "%LOG%\terminal.log" 2>&1"
start /b cmd /c "cd /d %ROOT%\webui && python wsserver.py                           > "%LOG%\wsserver.log" 2>&1"

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
echo  Type  stop  to shut everything down, or just close this window.
echo.

:loop
set "cmd="
set /p "cmd=> "
if /i "%cmd%"=="stop" goto shutdown
if /i "%cmd%"=="exit" goto shutdown
goto loop

:shutdown
echo Stopping EDLLM services...
call :killports
echo Done.
goto :eof

:killports
for %%P in (11434 8000 8001 8002) do (
  for /f "tokens=5" %%A in ('netstat -ano 2^>nul ^| findstr /r ":%P " ^| findstr LISTENING') do taskkill /PID %%A /F >nul 2>&1
)
taskkill /IM ollama.exe /F >nul 2>&1
goto :eof
