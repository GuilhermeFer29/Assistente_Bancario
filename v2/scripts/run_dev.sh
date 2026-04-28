#!/usr/bin/env bash
# Roda gateway, bot e streamlit localmente em background.
# Logs em /tmp/v2-{gateway,bot,streamlit}.log
# Uso: ./scripts/run_dev.sh start | stop | restart | logs

set -e
cd "$(dirname "$0")/.."

PYTHONPATH="$(pwd)"
export PYTHONPATH

GATEWAY_PID=/tmp/v2-gateway.pid
BOT_PID=/tmp/v2-bot.pid
ST_PID=/tmp/v2-streamlit.pid

start() {
  source .venv/bin/activate

  echo "▶ gateway na 8001..."
  nohup uvicorn assistente_bancario_v2.banking_gateway.app.main:app \
    --port 8001 --reload > /tmp/v2-gateway.log 2>&1 &
  echo $! > "$GATEWAY_PID"

  echo "▶ bot na 8000..."
  nohup uvicorn assistente_bancario_v2.bot_service.app.main:app \
    --port 8000 --reload > /tmp/v2-bot.log 2>&1 &
  echo $! > "$BOT_PID"

  echo "▶ streamlit na 8501..."
  nohup streamlit run frontend/streamlit_app.py \
    --server.port=8501 > /tmp/v2-streamlit.log 2>&1 &
  echo $! > "$ST_PID"

  sleep 2
  echo "✓ rodando. Logs em /tmp/v2-*.log"
}

stop() {
  for pid_file in "$GATEWAY_PID" "$BOT_PID" "$ST_PID"; do
    if [ -f "$pid_file" ]; then
      kill "$(cat "$pid_file")" 2>/dev/null || true
      rm -f "$pid_file"
    fi
  done
  echo "✓ serviços parados"
}

logs() {
  tail -f /tmp/v2-*.log
}

case "${1:-start}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop && start ;;
  logs)    logs ;;
  *)       echo "uso: $0 {start|stop|restart|logs}"; exit 1 ;;
esac
