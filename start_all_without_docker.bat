@echo off
title PolicyGraph-RAG Launcher (Without Docker)
echo =====================================================================
echo       PolicyGraph-RAG: Starting Application Without Docker
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/3] Generating sample insurance policies (PDFs)...
.\venv\Scripts\python.exe generate_sample_policy_pdfs.py

echo.
echo [2/3] Launching FastAPI Backend on http://localhost:8000 ...
start "PolicyGraph-RAG Backend (FastAPI)" cmd /k "cd /d ""%~dp0backend"" && call ""..\venv\Scripts\activate.bat"" && python -m uvicorn main:app --reload --port 8000"

echo.
echo [3/3] Launching Next.js Frontend on http://localhost:3000 ...
start "PolicyGraph-RAG Frontend (Next.js)" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Waiting 4 seconds for servers to initialize...
timeout /t 4 >nul

echo Opening browser at http://localhost:3000 ...
start http://localhost:3000

echo.
echo =====================================================================
echo  Services launched in separate windows!
echo   - Frontend:      http://localhost:3000
echo   - Backend API:   http://localhost:8000
echo   - Swagger Docs:  http://localhost:8000/docs
echo   - Sample PDFs:   %~dp0dataset\raw_pdfs\
echo =====================================================================
echo.
echo Keep the backend and frontend terminal windows open.
pause
