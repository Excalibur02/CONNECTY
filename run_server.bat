@echo off
title CONNECTY - FileShare Hub (FastAPI + Streamlit)
cd /d "%~dp0"
if not exist "server\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please install python venv first.
    pause
    exit /b 1
)
server\venv\Scripts\python.exe server\run_laptop.py
pause
