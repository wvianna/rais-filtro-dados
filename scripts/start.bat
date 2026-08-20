@echo off
rem ===========================================================================
rem  RAIS · Filtro de Dados — inicia o serviço web (Windows)
rem ---------------------------------------------------------------------------
rem  Instala o ambiente (venv + dependências) automaticamente, se necessário.
rem
rem  Uso:
rem    start.bat                        inicia em segundo plano (porta 8000)
rem    set PORT=9000 && start.bat       porta personalizada
rem    set HOST=0.0.0.0 && start.bat    escuta em todas as interfaces
rem
rem  O processo é gravado em run\server.pid e o log em run\server.log.
rem  Para encerrar: stop.bat
rem ===========================================================================
setlocal EnableExtensions
cd /d "%~dp0.."

if "%HOST%"=="" set "HOST=127.0.0.1"
if "%PORT%"=="" set "PORT=8000"
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

rem ------------------------------------------------------------------ 1. Python
where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado. Instale Python 3.10+ e adicione ao PATH.
  exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python 3.10+ e necessario.
  exit /b 1
)

rem ------------------------------------------------------- 2. Ambiente (venv)
if not exist "%VENV_PY%" (
  echo Ambiente virtual nao encontrado. Criando em %VENV_DIR% ...
  python -m venv "%VENV_DIR%"
  echo Ambiente virtual criado.
)

rem ------------------------------------------------ 3. Dependencias (opcional)
if exist requirements.txt (
  echo Instalando dependencias de requirements.txt ...
  "%VENV_PY%" -m pip install --quiet -r requirements.txt
)

rem ----------------------------------------------------- 4. Diretorio de execucao
if not exist run mkdir run

rem -------------------------------------------------- 5. Ja esta em execucao?
if exist run\server.pid (
  set /p OLDPID=<run\server.pid
  tasklist /FI "PID eq %OLDPID%" | findstr /C:"%OLDPID%" >nul 2>nul
  if not errorlevel 1 (
    echo Servico ja esta em execucao (PID %OLDPID%). URL: http://%HOST%:%PORT%/
    exit /b 0
  )
  del run\server.pid >nul 2>nul
)

rem --------------------------------------------- 6. Inicia em segundo plano
set "PYTHONPATH=%CD%\src"
powershell -NoProfile -Command ^
  "$p = Start-Process -FilePath '%VENV_PY%' -ArgumentList 'scripts\run_server.py','--host','%HOST%','--port','%PORT%' -WorkingDirectory '%CD%' -RedirectStandardOutput 'run\server.log' -RedirectStandardError 'run\server.err' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ascii 'run\server.pid'"

echo Servico iniciado. URL: http://%HOST%:%PORT%/
echo Para encerrar: stop.bat
exit /b 0
