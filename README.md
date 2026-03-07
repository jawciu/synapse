# synapse

Hackathon prototype for reflective journaling with a LangGraph + SurrealDB backend and now a TypeScript frontend path.

## Backend

- Python 3.12+ + LangGraph + SurrealDB.
- FastAPI app exposing reflection/chat/dashboard endpoints in [`api_server.py`](/Users/ian/dev/synapse/api_server.py).

## Frontend

- TypeScript/Vite React app under [`frontend/`](/Users/ian/dev/synapse/frontend).
- Modern charts via Recharts.
- Talks to the backend on `http://localhost:8000` by default.

## Quick start

1) Install `just` (if missing)

```bash
# Install Homebrew (macOS) if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install `just`:

```bash
brew install just
```

If you already have `just`, verify:

```bash
just --version
```

These commands are shell-agnostic and work from Bash, Zsh, Fish, etc.

2) Install Python deps

```bash
# Create .env with required values below before running services
just sync
```

`just sync` now runs:

- `uv sync` for Python dependencies.
- `npm install` inside `frontend/` (run as one command so it doesn't fail from the repo root).

3) Run core services

```bash
just dev
```

`just dev` starts:

- FastAPI on `http://localhost:8000`
- Vite on `http://localhost:5173`
- logs at `.tmp/synapse-api.log` and `.tmp/synapse-frontend.log`

Run Telegram separately (recommended) in another terminal:

```bash
just telegram
```

Or run all three in one terminal:

```bash
just dev-all
```

You can still run each service independently:

```bash
just backend
just frontend
just telegram
```

If you’re on a machine without `just` installed yet, retry step 1 first, then `just --list` and `just dev`.

Stop all services started by `just dev` or `just dev-all`:

```bash
just stop
```

If `just sync` still fails with `Could not read package.json` at `/Users/ian/dev/synapse/package.json`, you were likely using a pre-fix command; pull this patch then rerun `just sync`.

## Endpoints

- `GET /health`
- `GET /api/daily-prompt`
- `POST /api/reflection`
- `POST /api/chat`
- `GET /api/dashboard`

```json
// POST /api/reflection payload
{
  "reflection_text": "I had a hard week with feedback and shutdown.",
  "daily_prompt": "Optional prompt from backend",
  "thread_id": "optional client thread id"
}
```

## Required env

Add these to `.env` before running:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY` (required for reflection extraction)
- `SURREAL_URL`
- `SURREAL_NS`
- `SURREAL_DB`
- `SURREAL_USER`
- `SURREAL_PASS`

Optional:

- `CORS_ORIGINS` (comma-separated, default `http://localhost:5173`)
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT` (if tracing is enabled)
- `TELEGRAM_BOT_TOKEN` (required for `just telegram` and `just dev-all`)
