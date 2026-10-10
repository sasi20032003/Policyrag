@echo off
echo =====================================================================
echo    PolicyGraph-RAG: Local PostgreSQL & Database Initialization
echo =====================================================================
echo.

set PGUSER=postgres
set PGDATABASE=policygraph
set PGPORT=5432
set PGHOST=localhost

echo [1/3] Checking if PostgreSQL command 'psql' is in PATH...
where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: 'psql' was not found in your PATH.
    echo If PostgreSQL is installed, it is typically located at:
    echo   "C:\Program Files\PostgreSQL\<version>\bin"
    echo Please add the bin folder to your system PATH or run this from SQL Shell (psql).
    echo.
    pause
    exit /b 1
)

echo [2/3] Creating database '%PGDATABASE%' if it does not already exist...
psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -tc "SELECT 1 FROM pg_database WHERE datname = '%PGDATABASE%'" | findstr 1 >nul
if %ERRORLEVEL% NEQ 0 (
    echo Creating database %PGDATABASE%...
    psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -c "CREATE DATABASE %PGDATABASE%;"
) else (
    echo Database '%PGDATABASE%' already exists.
)

echo.
echo [3/3] Enabling pgvector extension in '%PGDATABASE%'...
psql -U %PGUSER% -h %PGHOST% -p %PGPORT% -d %PGDATABASE% -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo.
echo Setup completed! You can now run 'run_without_docker.bat'.
echo.
pause
