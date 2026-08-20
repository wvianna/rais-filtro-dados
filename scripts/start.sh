#!/usr/bin/env bash
# ============================================================================
# RAIS · Filtro de Dados — inicia o serviço web
# ----------------------------------------------------------------------------
# Uso:
#   scripts/start.sh                      # inicia em segundo plano (porta 8000)
#   scripts/start.sh --port 9000          # porta personalizada
#   scripts/start.sh --host 0.0.0.0       # escuta em todas as interfaces
#   scripts/start.sh --foreground         # roda em primeiro plano (Ctrl+C)
#
# Variáveis de ambiente:
#   HOST=...  PORT=...  PYTHON=...        # valores padrão: 127.0.0.1 · 8000 · python3
#
# O processo é gravado em run/server.pid e o log em run/server.log.
# Para encerrar: scripts/stop.sh (ou make stop).
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
PYTHON_BIN="${PYTHON:-python3}"
RUN_DIR="$ROOT/run"
PIDFILE="$RUN_DIR/server.pid"
LOGFILE="$RUN_DIR/server.log"
FOREGROUND=0

usage() {
  sed -n '3,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)      HOST="$2"; shift 2 ;;
    --port)      PORT="$2"; shift 2 ;;
    --foreground) FOREGROUND=1; shift ;;
    -h|--help)   usage ;;
    *) echo "Argumento desconhecido: $1" >&2; usage ;;
  esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Erro: Python não encontrado ('$PYTHON_BIN'). Defina PYTHON=..." >&2
  exit 1
fi

# Já está em execução?
if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Serviço já está em execução (PID $(cat "$PIDFILE")). URL: http://$HOST:$PORT/"
  exit 0
fi

mkdir -p "$RUN_DIR"

# Modo primeiro plano: executa no processo atual (sem pidfile persistente).
if [[ $FOREGROUND -eq 1 ]]; then
  echo "RAIS · Filtro de Dados — servidor em http://$HOST:$PORT/ (Ctrl+C para parar)"
  exec env PYTHONPATH="$ROOT/src" "$PYTHON_BIN" scripts/run_server.py --host "$HOST" --port "$PORT"
fi

# Segundo plano: registra PID e direciona o log.
nohup env PYTHONPATH="$ROOT/src" "$PYTHON_BIN" scripts/run_server.py \
  --host "$HOST" --port "$PORT" >>"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"

# Health check (sem depender de curl — usa a própria stdlib do Python).
_ping() {
  "$PYTHON_BIN" - "$HOST" "$PORT" <<'PY' 2>/dev/null
import sys, urllib.request
try:
    urllib.request.urlopen(f"http://{sys.argv[1]}:{sys.argv[2]}/api/health", timeout=2)
except Exception:
    sys.exit(1)
PY
}

URL="http://$HOST:$PORT/"
for _ in $(seq 1 20); do
  if _ping; then
    echo "Serviço iniciado. URL: $URL (PID $(cat "$PIDFILE"))"
    echo "Log: $LOGFILE   |   Para encerrar: scripts/stop.sh"
    exit 0
  fi
  sleep 0.5
done

echo "Aviso: o processo iniciou, mas o health check não respondeu." >&2
echo "Consulte o log: $LOGFILE" >&2
exit 1
