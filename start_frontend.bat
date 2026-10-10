@echo off
echo ========================================================
echo   Starting PolicyGraph-RAG Frontend (Next.js)
echo ========================================================
cd /d "%~dp0frontend"

echo Starting Next.js Dev Server at http://localhost:3000 ...
echo.
npm run dev
pause
