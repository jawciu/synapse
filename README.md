# synapse

**A stateful reflection agent powered by LangGraph + SurrealDB.**

Synapse turns journaling into a persistent knowledge graph, then lets users query that graph conversationally to surface patterns, triggers, and relationships over time.

Built for the **London LangChain x SurrealDB Hackathon**.

---

## The one-line pitch

Most AI journaling demos forget everything after each response. Synapse keeps durable, structured memory so the agent can reason across time instead of only reacting to the last message.

---

## Why this matters

Personal reflection is not a single-turn problem. Real insight comes from repeated patterns:

- the same trigger showing up across weeks
- the same person activating the same emotional loop
- the same body signal appearing before shutdown or anxiety

Synapse is designed to make that history queryable and useful.

---

## What we built

### 1) Reflection Ingestion Agent (LangGraph)

A 6-node pipeline processes each reflection:

1. `store_reflection`
2. `extract_patterns`
3. `update_graph`
4. `query_graph`
5. `generate_insights`
6. `generate_followups`

The graph starts with two parallel entry points (`store_reflection` and `extract_patterns`) and joins for graph updates.

### 2) Agentic extraction with retrieval grounding

Before extraction, the agent explicitly calls tools to:

- fetch existing patterns from the graph
- retrieve semantically similar reflections

That reduces duplicate labels and improves consistency over time.

### 3) Persistent memory in SurrealDB

Synapse stores both:

- **graph memory** (patterns, emotions, themes, IFS parts, schemas, people, body signals + typed edges)
- **vector memory** (semantic retrieval over reflections and embedded graph nodes)

### 4) Conversational "ask your graph" agent

A ReAct chat agent answers questions using 14 graph/search tools (including hybrid semantic graph search and person deep-dives), grounded in stored user data.

### 5) Product surfaces shipped

- Web app (React + TypeScript):
  - auth (register/login)
  - `reflect` tab for ingestion
  - `talk` tab for conversational analysis
  - interactive drill-downs for reflections, patterns, emotions, themes, people, and body signals
- API (FastAPI): reflection, chat (standard + streaming SSE), dashboard, people analytics
- Telegram bot: text and voice-note reflection ingestion (voice transcription via `whisper-1`)

---

## Why this is a strong LangChain x SurrealDB project

### Structured memory / knowledge usage (SurrealDB)

- Persistent graph entities and relations, not flat logs
- User-scoped storage with evolving node occurrence counts
- Graph + vector hybrid retrieval over the same knowledge surface

### Agent workflow quality (LangChain / LangGraph)

- Explicit multi-step pipeline with state handoff
- Tool-using extraction and tool-using chat agents
- Grounded answers based on graph lookups, not generic prompting

### Persistent agent state

- LangGraph `MemorySaver` thread continuity
- Durable storage in SurrealDB across sessions and channels (web + Telegram)

### Practical use case

- Real reflection workflow where longitudinal context is essential
- Actionable outputs: insights, follow-up questions, and relationship-focused key actions

### Observability

- LangSmith `@traceable` decorators across pipeline and graph operations

---

## Demo and judging materials

- Hackathon brief: [`london-hackathon-full-details.md`](/Users/ian/dev/synapse/london-hackathon-full-details.md)
- Full live-demo + video pitch playbook: [`pitch/PITCH_PLAYBOOK.md`](/Users/ian/dev/synapse/pitch/PITCH_PLAYBOOK.md)
- System architecture deep dive: [`ARCHITECTURE.md`](/Users/ian/dev/synapse/ARCHITECTURE.md)

---

## Tech stack

- **Orchestration:** LangGraph + LangChain
- **Backend:** FastAPI (Python 3.12+)
- **Frontend:** React + TypeScript (Vite)
- **Database:** SurrealDB (graph + vector)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Extraction + chat agents:** Anthropic `claude-sonnet-4-6`
- **Insight/follow-up generation:** OpenAI `gpt-5-mini`
- **Voice transcription (Telegram):** OpenAI `whisper-1`
- **Charts/UI analytics:** Recharts
- **Tracing:** LangSmith

---

## API surface

### Public health

- `GET /health`

### Auth

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/reset-request`
- `POST /api/auth/reset-confirm`

### Protected app routes (Bearer token required)

- `GET /api/daily-prompt`
- `POST /api/reflection`
- `POST /api/chat`
- `POST /api/chat/stream` (SSE)
- `GET /api/dashboard`
- `GET /api/people`
- `GET /api/reflections`

---

## Deployment

Render Blueprint file: [`render.yaml`](/Users/ian/dev/synapse/render.yaml)

Includes:

- `synapse-backend` (web)
- `synapse-telegram` (worker)
- `synapse-frontend` (static web)

---

## Local setup and run (keep this section at the bottom)

### 1) Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- npm
- [just](https://github.com/casey/just)

Install `just` on macOS:

```bash
brew install just
```

### 2) Configure environment

Create `.env` in the repo root.

Required:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `SURREAL_URL`
- `SURREAL_USER`
- `SURREAL_PASS`

Recommended defaults/optional:

- `SURREAL_NS=main` (or `SURREAL_NAMESPACE`)
- `SURREAL_DB=main` (or `SURREAL_DATABASE`)
- `JWT_SECRET=<random-long-secret>`
- `CORS_ORIGINS=http://localhost:5173`
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_PROJECT=synapse-hackathon`
- `LANGCHAIN_API_KEY=<if using LangSmith>`
- `TELEGRAM_BOT_TOKEN=<required for Telegram bot>`

### 3) Install dependencies

```bash
just sync
```

This runs backend dependency sync (`uv sync`) and frontend dependency sync when needed.

### 4) Run web app (backend + frontend)

```bash
just dev
```

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

Stop services:

```bash
just stop
```

### 5) Optional: run Telegram bot

Separate terminal:

```bash
just telegram
```

Or run all services in one terminal:

```bash
just dev-all
```

### 6) Open the app and authenticate

1. Visit `http://localhost:5173`
2. Register a new account (or log in)
3. Submit reflections in `reflect`
4. Query your graph in `talk`

### 7) Useful individual commands

```bash
just backend
just frontend
```

### 8) Notes

- `seed_data.py` is useful for pipeline experiments, but it does not attach a `user_id`; dashboard/chat views in the authenticated app are user-scoped.
- If frontend dependencies drift, rerun `just dev` or `just sync`.
