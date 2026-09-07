@echo off
title EDLLM - Stop all services
echo Stopping EDLLM services (ports 11434, 8000, 8001, 8002)...
for %%P in (11434 8000 8001 8002) do (
  for /f "tokens=5" %%A in ('netstat -ano 2^>nul ^| findstr /r ":%P " ^| findstr LISTENING') do taskkill /PID %%A /F >nul 2>&1
)
taskkill /IM ollama.exe /F >nul 2>&1
echo Done. All EDLLM services stopped.
timeout /t 2 >nul
