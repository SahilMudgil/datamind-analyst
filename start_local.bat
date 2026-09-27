@echo off
title DataMind Local Launcher
echo ===================================================
echo        Starting DataMind AI Text-to-SQL Analyst
echo                (Local Mode for MySQL & Postgres)
echo ===================================================
echo.

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

echo [1/3] Checking Python virtual environment...
if not exist "backend\.venv\Scripts\python.exe" (
    echo Virtual environment not found in backend\.venv. Creating...
    python -m venv backend\.venv
    call backend\.venv\Scripts\pip install -r backend\requirements.txt
)

echo [2/3] Starting Backend (FastAPI on port 8000)...
start "DataMind Backend" cmd /k "cd /d %ROOT_DIR%backend && .venv\Scripts\uvicorn main:app --reload --port 8000"

echo [3/3] Starting Frontend (React on port 3000)...
start "DataMind Frontend" cmd /k "cd /d %ROOT_DIR%frontend && npm run dev"

timeout /t 3 >nul
echo.
echo ===================================================
echo  DataMind is starting up!
echo  Opening browser at http://localhost:3000 ...
echo  Local MySQL (port 3306) and Postgres (port 5432/5433)
echo  can now be connected directly using "localhost"!
echo ===================================================
start http://localhost:3000
