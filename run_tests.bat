@echo off
echo ========================================================
echo   Running PolicyGraph-RAG Pytest Test Suite
echo ========================================================
cd /d "%~dp0backend"

if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python -m pytest -v
pause
