@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo          PolicyGraph-RAG: Local Launcher (Without Docker)
echo =====================================================================
echo.

cd /d "%~dp0"

:: 1. Check PostgreSQL port 5432
echo [1/4] Checking PostgreSQL connection on localhost:5432 ...
powershell -Command "$tcp = New-Object Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 5432); Write-Host '   [OK] PostgreSQL service is running on port 5432.'; $tcp.Close(); exit 0 } catch { Write-Host '   [WARN] Could not connect to PostgreSQL on port 5432.'; exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ---------------------------------------------------------------------
    echo  NOTE: PostgreSQL does not seem to be listening on localhost:5432.
    echo  If PostgreSQL is installed, make sure the service is started:
    echo    - Open 'services.msc' and start the PostgreSQL service, OR
    echo    - Run in Administrator CMD: net start postgresql-x64-16 (or your version)
    echo    - Ensure the database 'policygraph' exists: createdb -U postgres policygraph
    echo ---------------------------------------------------------------------
    echo.
    set /p CONTINUE="Do you want to proceed launching backend & frontend anyway? (y/n): "
    if /i "!CONTINUE!" NEQ "y" (
        echo Exiting launcher.
        pause
        exit /b 1
    )
)

:: 2. Launch Backend in a separate window
echo [2/4] Starting FastAPI Backend on http://localhost:8000 ...
start "PolicyGraph-RAG Backend (FastAPI)" cmd /k "cd /d ""%~dp0backend"" && (if exist ""..\venv\Scripts\activate.bat"" (call ""..\venv\Scripts\activate.bat"") else (call ""venv\Scripts\activate.bat"")) && uvicorn main:app --reload --port 8000"

:: 3. Launch Frontend in a separate window
echo [3/4] Starting Next.js Frontend on http://localhost:3000 ...
start "PolicyGraph-RAG Frontend (Next.js)" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

:: 4. Wait briefly and open browser
echo [4/4] Opening application in your default browser...
timeout /t 3 >nul
start http://localhost:3000

echo.
echo =====================================================================
echo  Application launched successfully!
echo   - Frontend:     http://localhost:3000
echo   - Backend API:  http://localhost:8000
echo   - Swagger Docs: http://localhost:8000/docs
echo =====================================================================
echo.
echo Leave the backend and frontend terminal windows open while using the app.
echo.
pause
