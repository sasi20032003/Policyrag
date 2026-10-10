@echo off
echo ========================================================
echo   Starting PolicyGraph-RAG Backend (FastAPI + pgvector)
echo ========================================================
cd /d "%~dp0backend"

if exist "..\venv\Scripts\activate.bat" (
    echo Activating virtual environment from ..\venv ...
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment from .\venv ...
    call "venv\Scripts\activate.bat"
) else (
    echo WARNING: Virtual environment not found. Using system Python...
)

echo.
echo Starting Uvicorn Server at http://localhost:8000 ...
echo Swagger API Documentation: http://localhost:8000/docs
echo.
python -m uvicorn main:app --reload --port 8000
pause
