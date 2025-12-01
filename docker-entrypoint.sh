#!/bin/bash
set -euo pipefail

python scripts/gerador_csv.py

uvicorn main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

echo "Backend iniciado (PID: $UVICORN_PID)"

STREAMLIT_PORT=${STREAMLIT_SERVER_PORT:-8501}
export BACKEND_WS_URL=${BACKEND_WS_URL:-ws://localhost:8000/chat/ws}

streamlit run frontend/streamlit_front.py \
  --server.port "$STREAMLIT_PORT" \
  --server.address 0.0.0.0 &
STREAMLIT_PID=$!

echo "Frontend iniciado (PID: $STREAMLIT_PID)"

trap "echo 'Encerrando serviços...'; kill $UVICORN_PID $STREAMLIT_PID" SIGINT SIGTERM
wait -n $UVICORN_PID $STREAMLIT_PID
