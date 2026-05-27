#!/usr/bin/env bash
set -euo pipefail

backend_host="${FASTAPI_BIND_HOST:-0.0.0.0}"
backend_port="${FASTAPI_PORT:-8000}"
frontend_host="${STREAMLIT_BIND_HOST:-0.0.0.0}"
frontend_port="${STREAMLIT_PORT:-8501}"

pids=()

shutdown() {
  local status=$?
  trap - SIGINT SIGTERM EXIT
  if ((${#pids[@]} > 0)); then
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
  exit "${status}"
}

trap shutdown SIGINT SIGTERM EXIT

python -m uvicorn src.backend.main:app \
  --host "${backend_host}" \
  --port "${backend_port}" \
  --reload &
pids+=("$!")

python -m streamlit run streamlit_app.py \
  --server.address="${frontend_host}" \
  --server.port="${frontend_port}" \
  --server.headless=true \
  --browser.gatherUsageStats=false &
pids+=("$!")

wait -n "${pids[@]}"
