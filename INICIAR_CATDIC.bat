@echo off
setlocal
cd /d "%~dp0BACKEND"
py -3.14 -m uvicorn main:app --host 127.0.0.1 --port 8000
if errorlevel 1 pause
