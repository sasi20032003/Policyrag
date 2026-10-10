@echo off
echo ===================================================
echo Generating PolicyGraph-RAG Review III Presentation
echo ===================================================

cd /d "%~dp0"

echo [1/2] Installing python-pptx in project venv...
.\venv\Scripts\pip.exe install python-pptx

echo.
echo [2/2] Creating PowerPoint deck...
.\venv\Scripts\python.exe create_presentation.py

echo.
if exist "PolicyGraph_RAG_Review_III_Presentation.pptx" (
    echo ===================================================
    echo SUCCESS! Presentation generated at:
    echo %~dp0PolicyGraph_RAG_Review_III_Presentation.pptx
    echo ===================================================
) else (
    echo [ERROR] Could not generate presentation. Please check error messages above.
)
pause
