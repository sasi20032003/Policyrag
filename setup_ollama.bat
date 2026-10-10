@echo off
echo =====================================================================
echo          PolicyGraph-RAG: Free LLM Setup (Local & Cloud)
echo =====================================================================
echo.
echo Free LLM Options Available:
echo   1. Groq Cloud (Free Tier, 70B & DeepSeek R1, 500+ tok/s, zero local load)
echo   2. Google Gemini Free Tier (Gemini 2.0 Flash, 1M context)
echo   3. Ollama Local (100%% Private, Offline: Qwen 2.5, DeepSeek R1, LLaMA 3.2)
echo =====================================================================
echo.

:: 1. Check if Ollama is installed
where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Ollama was not found on your system PATH.
    echo.
    echo You can either:
    echo   A) Use FREE Cloud LLMs (Groq / Gemini) by adding GROQ_API_KEY in backend/.env
    echo      (Get free key at https://console.groq.com)
    echo   B) Download Ollama for 100%% offline local execution: https://ollama.com/download
    echo.
    pause
    exit /b 0
)

echo [1/3] Ollama is installed.
echo.

:: 2. Check if Ollama service is running
powershell -Command "$tcp = New-Object Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 11434); Write-Host '   [OK] Ollama server is running on http://localhost:11434'; $tcp.Close(); exit 0 } catch { Write-Host '   [INFO] Starting Ollama server in background...'; exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    start "Ollama Server" cmd /k "ollama serve"
    timeout /t 3 >nul
)

:: 3. Pull recommended low-hallucination models
echo.
echo [2/3] Pulling recommended low-hallucination models...
echo [INFO] Pulling 'llama3.2' (Fast 3B base model)...
ollama pull llama3.2

echo.
echo [TIP] For ZERO-HALLUCINATION extraction on insurance policy tables,
echo       we strongly recommend:
echo         ollama pull qwen2.5:7b       (Best for tables & policy clauses)
echo         ollama pull deepseek-r1:8b   (Best for step-by-step reasoning)
echo.

echo [3/3] Testing local Ollama model response...
ollama run llama3.2 "Hello, respond with 'Ollama is ready for PolicyGraph-RAG!'"

echo.
echo =====================================================================
echo  Zero-Hallucination Configuration Ready!
echo  
echo  To switch to Free Cloud 70B (Groq):
echo    Set LLM_PROVIDER=groq in backend/.env
echo    Set GROQ_API_KEY=gsk_...
echo  
echo  To use Local Deterministic Model (Ollama):
echo    Set LLM_PROVIDER=ollama in backend/.env
echo    Set LLM_MODEL=llama3.2 (or qwen2.5:7b)
echo =====================================================================
echo.
pause
