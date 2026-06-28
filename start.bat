@echo off
title QA Copilot

echo Starting QA Copilot...

:: Start backend in background
start "QA Copilot Backend" /min cmd /c "cd /d %~dp0 && uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: Wait for backend to be ready
echo Waiting for backend...
timeout /t 4 /nobreak >nul

:: Open Chrome
start "" "chrome.exe" "http://localhost:8501"

:: Start Streamlit (this window stays open - closing it stops the UI)
cd /d %~dp0
python -m streamlit run frontend/app.py --browser.serverAddress localhost --server.port 8501
