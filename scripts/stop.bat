@echo off
rem ===========================================================================
rem  RAIS · Filtro de Dados — encerra o serviço web iniciado por start.bat
rem ---------------------------------------------------------------------------
rem  Lê o PID em run\server.pid, encerra o processo (e força se necessário)
rem  e remove o pidfile. O log (run\server.log) é preservado.
rem ===========================================================================
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist run\server.pid (
  echo Servico nao esta em execucao (nao ha run\server.pid).
  exit /b 0
)

set /p PID=<run\server.pid

rem Confere se o processo ainda existe
tasklist /FI "PID eq %PID%" | findstr /C:"%PID%" >nul 2>nul
if errorlevel 1 (
  echo Servico nao esta em execucao (PID %PID% nao encontrado). Removendo pidfile.
  del run\server.pid >nul 2>nul
  exit /b 0
)

echo Encerrando servico RAIS (PID %PID%)...
taskkill /PID %PID% >nul 2>nul
if errorlevel 1 (
  echo Processo nao respondeu; forçando encerramento.
  taskkill /PID %PID% /F >nul 2>nul
)

del run\server.pid >nul 2>nul
echo Servico encerrado.
exit /b 0
