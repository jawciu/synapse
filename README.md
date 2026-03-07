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
- frontend dependency sync (`npm install`) when `frontend/node_modules` is missing or stale vs `frontend/package-lock.json`.

3) Run core services

```bash
just dev
```

`just dev` starts:

- FastAPI on `http://localhost:8000`
- Vite on `http://localhost:5173`
- auto-installs frontend deps first if missing/stale
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

`just frontend` also auto-installs frontend deps first if needed.

If you’re on a machine without `just` installed yet, retry step 1 first, then `just --list` and `just dev`.

Stop all services started by `just dev` or `just dev-all`:

```bash
just stop
```

If `just sync` still fails with `Could not read package.json` at `/Users/ian/dev/synapse/package.json`, you were likely using a pre-fix command; pull this patch then rerun `just sync`.
If Vite reports `Failed to resolve import ...` for a package that exists in `frontend/package.json`, rerun `just dev` (or `just frontend`) and the dependency sync step will install missing modules.

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
- `JWT_SECRET` (random hex string used to sign auth tokens)

## Auth

All data endpoints require a JWT bearer token. Register or log in via the web UI at `http://localhost:5173` to get a token, which is stored in `localStorage` and sent automatically.

Auth endpoints (no token required):

- `POST /api/auth/register` — `{ email, password }` → `{ user_id, email, token }`
- `POST /api/auth/login` — `{ email, password }` → `{ user_id, email, token }`
- `POST /api/auth/reset-request` — `{ email }` → `{ reset_token }` (token returned in response, no email sent)
- `POST /api/auth/reset-confirm` — `{ token, new_password }`

## Telegram bot

Start the bot with `just telegram`. On first contact from an unknown user the bot walks them through account creation inline:

1. Bot asks for email
2. User replies with their email
3. Bot asks for password
4. User replies with password → account created, `telegram_id` linked, reflection processed

Subsequent messages are automatically identified by `telegram_id` — no login needed.

**Linking an existing web account to Telegram**: send `/link` to the bot, then provide your email and password when prompted.

**If you had data before auth was added**: run the migration script to assign all orphaned records to a new account:

```bash
uv run python migrate_orphans.py you@example.com yourpassword
```
