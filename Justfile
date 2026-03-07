default:
  @just --list

PORT_API := "8000"
PORT_FRONTEND := "5173"
API_URL := "http://localhost:8000"

# Install backend and frontend dependencies.
sync:
  uv sync
  (cd frontend && npm install)

# Run the FastAPI backend.
backend:
  uv run uvicorn api_server:app --reload --host 0.0.0.0 --port {{PORT_API}}

# Run the React frontend.
frontend:
  (cd frontend && VITE_API_URL={{API_URL}} npm run dev -- --host 0.0.0.0 --port {{PORT_FRONTEND}})

# Run the Telegram bot.
telegram:
  uv run python -m reflect.telegram_bot

# Run backend + frontend in one terminal.
# Press Ctrl+C to stop all processes.
dev:
  mkdir -p .tmp; \
  if [ -f .tmp/synapse-pids ]; then \
    . .tmp/synapse-pids; \
    kill ${API_PID:-} ${FRONTEND_PID:-} ${TELEGRAM_PID:-} >/dev/null 2>&1 || true; \
  fi; \
  rm -f .tmp/synapse-pids; \
  uv run uvicorn api_server:app --reload --host 0.0.0.0 --port {{PORT_API}} > .tmp/synapse-api.log 2>&1 & \
  API_PID=$!; \
  (cd frontend && VITE_API_URL={{API_URL}} npm run dev -- --host 0.0.0.0 --port {{PORT_FRONTEND}}) > .tmp/synapse-frontend.log 2>&1 & \
  FRONTEND_PID=$!; \
  echo "API_PID=$API_PID" > .tmp/synapse-pids; \
  echo "FRONTEND_PID=$FRONTEND_PID" >> .tmp/synapse-pids; \
  echo "Running Synapse"; \
  echo "Backend:  http://localhost:{{PORT_API}}"; \
  echo "Frontend: http://localhost:{{PORT_FRONTEND}}"; \
  echo "Telegram bot: not started (run separately with: just telegram)"; \
  echo "Stop with: just stop"; \
  trap 'kill $API_PID $FRONTEND_PID >/dev/null 2>&1 || true' INT TERM EXIT; \
  tail -f .tmp/synapse-api.log .tmp/synapse-frontend.log

# Run backend + frontend + Telegram in one terminal.
# Press Ctrl+C to stop all processes.
dev-all:
  mkdir -p .tmp; \
  if [ -f .tmp/synapse-pids ]; then \
    . .tmp/synapse-pids; \
    kill ${API_PID:-} ${FRONTEND_PID:-} ${TELEGRAM_PID:-} >/dev/null 2>&1 || true; \
  fi; \
  rm -f .tmp/synapse-pids; \
  uv run uvicorn api_server:app --reload --host 0.0.0.0 --port {{PORT_API}} > .tmp/synapse-api.log 2>&1 & \
  API_PID=$!; \
  (cd frontend && VITE_API_URL={{API_URL}} npm run dev -- --host 0.0.0.0 --port {{PORT_FRONTEND}}) > .tmp/synapse-frontend.log 2>&1 & \
  FRONTEND_PID=$!; \
  uv run python -m reflect.telegram_bot > .tmp/synapse-telegram.log 2>&1 & \
  TELEGRAM_PID=$!; \
  echo "API_PID=$API_PID" > .tmp/synapse-pids; \
  echo "FRONTEND_PID=$FRONTEND_PID" >> .tmp/synapse-pids; \
  echo "TELEGRAM_PID=$TELEGRAM_PID" >> .tmp/synapse-pids; \
  echo "Running Synapse"; \
  echo "Backend:  http://localhost:{{PORT_API}}"; \
  echo "Frontend: http://localhost:{{PORT_FRONTEND}}"; \
  echo "Telegram bot: enabled (logs: .tmp/synapse-telegram.log)"; \
  echo "Stop with: just stop"; \
  trap 'kill $API_PID $FRONTEND_PID $TELEGRAM_PID >/dev/null 2>&1 || true' INT TERM EXIT; \
  tail -f .tmp/synapse-api.log .tmp/synapse-frontend.log .tmp/synapse-telegram.log

# Stop services started by `just dev` or `just dev-all`.
stop:
  @if [ -f .tmp/synapse-pids ]; then \
    . .tmp/synapse-pids; \
    kill ${API_PID:-} ${FRONTEND_PID:-} ${TELEGRAM_PID:-} >/dev/null 2>&1 || true; \
    rm -f .tmp/synapse-pids; \
    echo "Stopped synapse processes"; \
  else \
    echo "No synapse process file found at .tmp/synapse-pids"; \
  fi
