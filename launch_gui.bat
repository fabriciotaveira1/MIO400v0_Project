@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" launcher.py
) else (
    python launcher.py
)

if errorlevel 1 (
    echo.
    echo Launcher terminou com erro. Veja as mensagens acima.
    pause
)
