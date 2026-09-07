@echo off
REM One-click launcher: Ollama + web chat UI + local terminal, opens Chrome.
set OLLAMA_MODELS=F:\tmp\Model
set OLLAMA_ORIGINS=*

taskkill /IM ollama.exe /F >nul 2>&1
timeout /t 1 >nul

start "Ollama-Server" cmd /k "set OLLAMA_MODELS=F:\tmp\Model && set OLLAMA_ORIGINS=* && echo Ollama server (models: F:\tmp\Model) && ollama serve"
start "WebUI" cmd /k "cd /d F:\tmp\Model\webui && echo Web UI: http://localhost:8000 && python -m http.server 8000"
start "Terminal" cmd /k "cd /d F:\tmp\Model\webui && echo Terminal API: http://localhost:8001 && python terminal.py"
start "TerminalWS" cmd /k "cd /d F:\tmp\Model\webui && echo Terminal WS: ws://localhost:8002 && python wsserver.py"

timeout /t 3 >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:8000 2>nul || start chrome http://localhost:8000 2>nul || start http://localhost:8000

echo.
echo EDLLM starting...
echo   Chat:        http://localhost:8000
echo   Terminal API: http://localhost:8001
echo   Terminal WS:  ws://localhost:8002
echo   Ollama:       http://localhost:11434
pause
