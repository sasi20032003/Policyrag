@echo off
echo ========================================================
echo   Starting PolicyGraph-RAG Stack via Docker Compose
echo ========================================================
cd /d "%~dp0"

echo Launching PostgreSQL (pgvector), Backend, and Frontend containers...
docker compose up -d

echo.
echo Containers started!
echo - Database: localhost:5432
echo - Backend API: http://localhost:8000 (Docs: http://localhost:8000/docs)
echo - Frontend: http://localhost:3000
echo.
pause
