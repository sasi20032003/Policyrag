@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo    PolicyGraph-RAG: Launch Application & Pipeline With Live Data
echo =====================================================================
echo.

cd /d "%~dp0"

echo [STEP 1/3] Generating Realistic Sample Insurance Policies (PDFs)...
.\venv\Scripts\python.exe generate_sample_policy_pdfs.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to generate PDFs. Please verify python venv.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo [STEP 2/3] Running PolicyGraph-RAG Hybrid (OKF + Evidence) Verification
echo =====================================================================
echo.
.\venv\Scripts\python.exe demo_rag_vs_okf_comparison.py

echo.
echo =====================================================================
echo [STEP 3/3] Launching Full-Stack Services (FastAPI + Next.js Web UI)
echo =====================================================================
echo.

:: Check if Docker is available
where docker >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Docker detected on your system.
    set /p DOCKER_LAUNCH="Do you want to launch the Full Web App via Docker Compose? (y/n): "
    if /i "!DOCKER_LAUNCH!"=="y" (
        echo Launching Docker Compose stack (pgvector + backend + frontend)...
        docker compose up -d
        echo.
        echo Opening Web Application in your browser...
        timeout /t 3 >nul
        start http://localhost:3000
        echo.
        echo Application running!
        echo   - Frontend:    http://localhost:3000
        echo   - Backend API: http://localhost:8000
        echo   - Swagger Doc: http://localhost:8000/docs
        pause
        exit /b 0
    )
)

echo.
echo Running local launcher (run_without_docker.bat)...
call run_without_docker.bat
pause
