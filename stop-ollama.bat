@echo off
title EDLLM - Stop all services
echo Stopping EDLLM services (ports 11434, 8000, 8001, 8002)...
for %%P in (11434 8000 8001 8002) do (
  for /f "tokens=1,2,3,4,5" %%a in ('netstat -ano 2^>nul ^| findstr LISTENING') do (
    echo %%b | findstr /r ":%P " >nul 2>&1 && taskkill /PID %%e /F >nul 2>&1
  )
)
taskkill /IM ollama.exe /F >nul 2>&1
echo Done. All EDLLM services stopped.
timeout /t 2 >nul
