@echo off
title CONNECTY FastAPI Backend Service
cd /d "%~dp0"
server\venv\Scripts\python.exe server\run.py
pause
