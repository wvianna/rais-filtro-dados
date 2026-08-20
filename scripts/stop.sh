#!/usr/bin/env bash
# ============================================================================
# RAIS · Filtro de Dados — encerra o serviço web iniciado por scripts/start.sh
# ----------------------------------------------------------------------------
# Lê o PID em run/server.pid, encerra o processo (com graça, e força se
# necessário) e remove o pidfile. O log (run/server.log) é preservado.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PIDFILE="$ROOT/run/server.pid"
LOGFILE="$ROOT/run/server.log"

if [[ ! -f "$PIDFILE" ]]; then
  echo "Serviço não está em execução (não há run/server.pid)."
  exit 0
fi

PID="$(cat "$PIDFILE")"

if ! kill -0 "$PID" 2>/dev/null; then
  echo "Serviço não está em execução (PID $PID não encontrado). Removendo pidfile."
  rm -f "$PIDFILE"
  exit 0
fi

echo "Encerrando serviço RAIS (PID $PID)..."
kill "$PID" 2>/dev/null || true

# Aguarda o encerramento gracioso (até ~5 s).
for _ in $(seq 1 20); do
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

# Força o encerramento se ainda estiver vivo.
if kill -0 "$PID" 2>/dev/null; then
  echo "Processo não respondeu; forçando (kill -9)."
  kill -9 "$PID" 2>/dev/null || true
fi

rm -f "$PIDFILE"
echo "Serviço encerrado."
[[ -f "$LOGFILE" ]] && echo "Log preservado em: $LOGFILE"
