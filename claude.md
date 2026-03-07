# synapse

This file is the working project brief for agents.

Read this file before making changes. If you change architecture, product behavior, prompts, data model, dependencies, runtime commands, or repo structure, update this file in the same turn so it does not drift.

## What this project is

This repo is a hackathon prototype for a self-reflection journaling app that turns journal entries into a persistent psychological pattern graph.

The product intent is:

- Let a user write a reflection.
- Extract recurring patterns, emotions, themes, inner parts, schemas, people, and body signals from that reflection.
- Store those concepts in SurrealDB as both graph data and semantic vectors.
- Use the accumulated graph to surface historical patterns, likely roots, and follow-up questions.
- Let the user query their graph conversationally afterward.

The product should be treated as `synapse` in the UI and agent-facing docs. Older planning language still mentions `ReflectGraph`, but that is now legacy naming.

The strongest source of product intent is [PLAN.md](/Users/ian/dev/synapse/PLAN.md). The strongest source of truth for actual behavior is the code under [reflect/](/Users/ian/dev/synapse/reflect).

## Current implementation status

The repo is small but mostly complete as a demo:

- Python backend service and TypeScript frontend entrypoint.
- LangGraph pipeline for ingestion and analysis.
- LangGraph ReAct chat agent for querying stored graph data.
- SurrealDB used both as graph store and vector store backend.
- OpenAI is used for embeddings, insight/follow-up synthesis, and Telegram voice transcription; Anthropic is used for extraction and chat agents.
- LangSmith decorators are present on the main pipeline and graph functions.
- Seed data exists and is intentionally written to create cross-entry childhood and relationship patterns.
- Reflect UI behavior: reflection editor is hidden until the user clicks `Use prompt` or `Start fresh`; `Use prompt` inserts a structured draft template with placeholders; `Start fresh` opens a compact ask-style input; `Cmd+Enter`/`Ctrl+Enter` submits the reflection composer; extracted entity sections (patterns, emotions, themes, IFS parts, schemas, people, body signals) render only when that reflection includes updates; the primary submit action is a centered `reflect` button.
- Reflection records now track a `source` value (`app`, `telegram_text`, or `voice`) and `/api/reflections` returns it for source attribution in the UI.
- SurrealDB startup now validates required env vars with clear `RuntimeError` messages; namespace/database default to `main` when unset and also accept `SURREAL_NAMESPACE` / `SURREAL_DATABASE` aliases.
- Render Blueprint config exists in `render.yaml` for backend (`synapse-backend`), Telegram worker (`synapse-telegram`), and static frontend (`synapse-frontend`) with `autoDeploy: true` on `main`.
- Public frontend demo is currently available at `https://synapse-frontend-vdmo.onrender.com/`.
- Public Telegram bot handle is `@synapse_helper_bot` (`https://t.me/synapse_helper_bot`).
- Local reusable skill pack now exists under `.claude/skills/` in agentskills.io-style layout (`SKILL.md` + `agents/openai.yaml`) for `langchain`, `surrealdb`, `vite-typescript`, and `python`.
- The reflections source panel supports frontend sort/filter/search controls (by source, date order, and text query) for faster drill-down.
- Clicking the `people` total now opens a graph-backed people drill-down sourced from `/api/people`, including a key action callout, relationship mix chart, top-triggered-pattern chart, and per-person triggered-pattern details.
- Clicking `patterns`, `emotions`, `themes`, and `body signals` totals now opens dedicated graph drill-downs (key action + KPI row + charts + item list) instead of a placeholder message.
- The dedicated `patterns` tab has been removed from the primary tab bar; primary tabs are now `reflect` and `talk` while totals in the top menubar continue to expose source/drill-down panels.
- The `talk` tab now uses an empty-first UX: a centered question composer appears immediately, and the larger transcript panel is only rendered after the first message is sent.

What is not present:

- No real test suite.
- No advanced auth features (for example roles/permissions, admin controls, or external identity providers).
- No production hardening around failures, retries, schema migrations, or privacy.

## Tech stack

- Python 3.12+ via [pyproject.toml](/Users/ian/dev/synapse/pyproject.toml)
- FastAPI for API transport (`api_server.py`)
- TypeScript React frontend (Vite) in `frontend/` for the primary product UI
- LangGraph / LangChain for orchestration and agents
- OpenAI:
  - `gpt-5-mini` for insights and follow-up generation
  - `gpt-4o-mini` in [main.py](/Users/ian/dev/synapse/main.py) (scratch smoke test) and Telegram nudge generation
  - `whisper-1` for Telegram voice-note transcription
  - `text-embedding-3-small` for embeddings
- Anthropic:
  - `claude-sonnet-4-6` for extraction and chat (`ANTHROPIC_API_KEY` required)
- SurrealDB for:
  - structured graph tables and relations
  - vector search over reflection documents
  - vector search over embedded graph nodes
- Recharts for charts in the new TypeScript dashboard
- `langchain-surrealdb` with local query/index patches for SurrealDB v3 compatibility

## Repo map

- [PLAN.md](/Users/ian/dev/synapse/PLAN.md): intended architecture and hackathon framing
- [README.md](/Users/ian/dev/synapse/README.md): public-facing project pitch with user quickstart, Telegram text/voice usage, architecture narrative, and local runbook
- [london-hackathon-full-details.md](/Users/ian/dev/synapse/london-hackathon-full-details.md): full event brief and judging/submission details for the London LangChain x SurrealDB hackathon
- [pitch/PITCH_PLAYBOOK.md](/Users/ian/dev/synapse/pitch/PITCH_PLAYBOOK.md): live demo script, 2-minute video plan, and pitch execution checklist
- [.claude/skills/](/Users/ian/dev/synapse/.claude/skills): local agent skills in agentskills.io format (`langchain`, `surrealdb`, `vite-typescript`, `python`)
- [pyproject.toml](/Users/ian/dev/synapse/pyproject.toml): dependencies and Python version
- [render.yaml](/Users/ian/dev/synapse/render.yaml): Render Blueprint for `synapse-backend` web + `synapse-telegram` worker + `synapse-frontend` static service with `autoDeploy: true`
- [main.py](/Users/ian/dev/synapse/main.py): simple OpenAI smoke test, not the product entrypoint
- [seed_data.py](/Users/ian/dev/synapse/seed_data.py): runs the full reflection pipeline over the sample corpus
- [langchain_surreal.py](/Users/ian/dev/synapse/langchain_surreal.py): standalone vector-store experiment / proof of concept
- [surreal_test.py](/Users/ian/dev/synapse/surreal_test.py): standalone SurrealDB CRUD experiment
- [test.py](/Users/ian/dev/synapse/test.py): trivial environment sanity check
- [data/sample_reflections/](/Users/ian/dev/synapse/data/sample_reflections): 18 curated seed reflections
- [reflect/db.py](/Users/ian/dev/synapse/reflect/db.py): env loading, Surreal connection, embedding model, vector store creation, schema setup, Surreal v3 patching
- [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py): graph CRUD, edge creation, graph queries, and all agent tools
- [reflect/extraction.py](/Users/ian/dev/synapse/reflect/extraction.py): extraction ReAct agent wrapper and JSON parsing
- [reflect/agent.py](/Users/ian/dev/synapse/reflect/agent.py): 6-node LangGraph reflection pipeline
- [reflect/chat_agent.py](/Users/ian/dev/synapse/reflect/chat_agent.py): graph Q&A ReAct agent
- [reflect/prompts.py](/Users/ian/dev/synapse/reflect/prompts.py): extraction/chat/insight/follow-up prompts plus daily prompts
- [api_server.py](/Users/ian/dev/synapse/api_server.py): FastAPI app exposing reflection/chat/dashboard routes, `/api/people` for relationship drill-down analytics, plus `/api/reflections` for reflection source retrieval with source metadata (`app` / `telegram_text` / `voice`)
- [frontend/](/Users/ian/dev/synapse/frontend): Vite + TypeScript React UI scaffold
- [frontend/src/icons.tsx](/Users/ian/dev/synapse/frontend/src/icons.tsx): local OSS-style SVG icon components used by the navbar and prompt refresh action

## Runtime model

There are two distinct agentic systems in the app.

### 1. Reflection ingestion pipeline

Implemented in [reflect/agent.py](/Users/ian/dev/synapse/reflect/agent.py).

The reflection flow is:

1. `store_reflection`
2. `extract_patterns`
3. `update_graph`
4. `query_graph`
5. `generate_insights`
6. `generate_followups`

Compiled with `MemorySaver`.

Important details:

- Shared resources are lazily initialized in `_init()`.
- `_init()` connects to SurrealDB, runs schema initialization every process start, creates embeddings, patches the vector store, and builds tool sets.
- Each submitted reflection uses an auto-generated thread id like `reflection-session-<uuid>` when one is not provided.
- Reflection text is stored twice:
  - as a `reflection` record in the graph
  - as a vector-store document for semantic retrieval

### 2. Ask-your-graph chat agent

Implemented in [reflect/chat_agent.py](/Users/ian/dev/synapse/reflect/chat_agent.py) using tools created in [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py).

Important details:

- Uses `create_react_agent`.
- Uses `claude-sonnet-4-6`.
- Uses `MemorySaver`.
- Chat messages use `thread_id` values managed by the frontend (`chat-session*` when omitted) so context can continue across turns.

## Data flow in detail

### Reflection submit flow

When a user submits text in the Reflect tab:

1. The frontend submits `/api/reflection`.
2. The backend runs `graph.invoke(...)`.
3. The reflection text and current daily prompt are saved to `reflection`.
4. The same text is embedded and added to the Surreal-backed vector store.
5. The extraction agent is run on the reflection text.
6. Extracted entities are upserted into graph tables.
7. Edges are created between the reflection and extracted nodes.
8. Several graph queries are run to collect historical context.
9. A separate LLM call generates short insight text.
10. Another LLM call generates exactly 3 follow-up questions.
11. The UI renders extracted entities, insights, and follow-ups.

### Extraction flow

Implemented in [reflect/extraction.py](/Users/ian/dev/synapse/reflect/extraction.py) and driven by `EXTRACTION_SYSTEM_PROMPT` in [reflect/prompts.py](/Users/ian/dev/synapse/reflect/prompts.py).

This is an agentic extraction pattern, not a single raw prompt:

- Tool 1: `get_existing_patterns`
- Tool 2: `retrieve_similar_reflections`

The prompt explicitly instructs the model to call both before extracting so it can reuse existing labels and stay more graph-consistent over time.

The output is expected to be JSON only with:

- `patterns`
- `emotions`
- `themes`
- `ifs_parts`
- `schemas`
- `people`
- `body_signals`

If JSON parsing fails, extraction falls back to an empty structure instead of crashing.

Provider/runtime behavior:

- extraction is Anthropic-only and requires `ANTHROPIC_API_KEY`
- if extraction model invocation fails, extraction returns an empty structure so `/api/reflection` does not fail at extraction time

### Graph update flow

Implemented in [reflect/agent.py](/Users/ian/dev/synapse/reflect/agent.py) and [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py).

The update step:

- upserts patterns
- upserts themes
- upserts emotions
- upserts IFS parts
- upserts schema patterns
- upserts people
- upserts body signals
- creates all cross-node relations

### Insight generation flow

This is not graph-native reasoning by itself. It is an LLM synthesis step over:

- the current raw reflection
- the current extraction JSON
- a small set of graph query results:
  - top co-occurrences
  - negative emotion triggers
  - most connected patterns

### Follow-up generation flow

This is another separate LLM call that uses:

- extracted pattern names
- extracted people names
- extracted body signals
- generated insights

If the follow-up LLM output cannot be parsed, it falls back to 3 generic questions.

## SurrealDB architecture

Implemented in [reflect/db.py](/Users/ian/dev/synapse/reflect/db.py).

The code assumes environment variables for:

- `SURREAL_URL`
- `SURREAL_NS` (optional, defaults to `main`; alias: `SURREAL_NAMESPACE`)
- `SURREAL_DB` (optional, defaults to `main`; alias: `SURREAL_DATABASE`)
- `SURREAL_USER`
- `SURREAL_PASS`
- `OPENAI_API_KEY`

LangSmith keys are implied by the tracing decorators and the plan doc, though this repo does not validate them at startup.

### SurrealDB v3 patching

This repo directly patches `langchain_surrealdb.vectorstores` globals to make the package work with SurrealDB v3:

- swaps vector index creation to HNSW
- uses explicit `COSINE` KNN syntax
- returns `vector::distance::knn()` as the similarity metric

This is an important implementation detail. If vector search breaks after package upgrades, check [reflect/db.py](/Users/ian/dev/synapse/reflect/db.py) first.

## Graph schema

The schema is defined in `SCHEMA_STATEMENTS` in [reflect/db.py](/Users/ian/dev/synapse/reflect/db.py).

### Node tables

- `reflection`
  - `text`
  - `created_at`
  - `daily_prompt`
  - `source`
- `pattern`
  - `name`
  - `category`
  - `description`
  - `occurrences`
  - `first_seen`
  - `last_seen`
  - `embedding`
- `theme`
  - `name`
  - `description`
  - `embedding`
- `emotion`
  - `name`
  - `valence`
  - `intensity`
- `ifs_part`
  - `name`
  - `role`
  - `description`
  - `occurrences`
  - `first_seen`
  - `last_seen`
  - `embedding`
- `schema_pattern`
  - `name`
  - `domain`
  - `coping_style`
  - `description`
  - `occurrences`
  - `first_seen`
  - `last_seen`
  - `embedding`
- `person`
  - `name`
  - `relationship`
  - `description`
  - `occurrences`
  - `first_seen`
  - `last_seen`
  - `embedding`
- `body_signal`
  - `name`
  - `location`
  - `occurrences`

### Relation tables

- `reveals` from `reflection` to `pattern`
- `expresses` from `reflection` to `emotion`
- `about` from `reflection` to `theme`
- `co_occurs_with` from `pattern` to `pattern`
- `triggered_by` from `emotion` to `theme`
- `activates` from `reflection` to `ifs_part`
- `triggers_schema` from `reflection` to `schema_pattern`
- `protects_against` from `ifs_part` to `schema_pattern`
- `mentions` from `reflection` to `person`
- `triggers_pattern` from `person` to `pattern`
- `reminds_of` from `person` to `person`
- `feels_in_body` from `reflection` to `body_signal`

### Vectorized graph nodes

These tables have embedding fields plus HNSW indexes:

- `pattern`
- `theme`
- `ifs_part`
- `schema_pattern`
- `person`

`emotion` and `body_signal` are not embedded.

Reflection text vectors live separately in the vector-store documents table managed by `langchain-surrealdb`.

## Graph semantics

The graph is trying to represent recurring reflective structure across several therapy-inspired lenses:

- CBT-style cognitive patterns
- DBT-style emotional dynamics
- IFS-style protective or wounded parts
- Schema Therapy patterns and coping styles
- relationship/person-trigger links
- body-based markers

There is no diagnosis logic. Everything is framed as reflective pattern extraction.

## Query and tool layer

Most graph intelligence lives in [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py).

### Core CRUD helpers

- `store_reflection_record`
- `upsert_pattern`
- `upsert_theme`
- `upsert_emotion`
- `upsert_ifs_part`
- `upsert_schema`
- `upsert_person`
- `upsert_body_signal`
- `create_edges`

### Direct graph query helpers

- `query_patterns_by_theme`
- `query_co_occurrences`
- `query_pattern_evolution`
- `query_negative_emotion_triggers`
- `query_central_patterns`
- `query_all_patterns`

### Extraction agent tools

- `retrieve_similar_reflections`
- `get_existing_patterns`

### Chat agent tools

- `hybrid_graph_search`
- `get_all_patterns_overview`
- `get_all_emotions_overview`
- `get_ifs_parts_overview`
- `get_schemas_overview`
- `get_people_overview`
- `get_person_deep_dive`
- `get_body_signals_overview`
- `get_deep_pattern_analysis`
- `get_graph_summary`
- `get_emotion_triggers`
- `get_pattern_connections`
- `get_temporal_evolution`
- `semantic_search_reflections`

### Important tool behavior notes

- `hybrid_graph_search` semantically searches embedded node tables, not reflection documents.
- `semantic_search_reflections` and `retrieve_similar_reflections` search the vectorized reflection documents.
- `get_ifs_parts_overview` and `get_schemas_overview` are the best tools for childhood-roots / pattern-origin questions because they attach source reflection text.
- `get_people_overview` and `get_person_deep_dive` are the key relationship-analysis tools.

## UI architecture

Primary implementation is now an API-driven frontend split:

- [api_server.py](/Users/ian/dev/synapse/api_server.py) exposes `/api/*` endpoints.
- [frontend/](/Users/ian/dev/synapse/frontend) renders the primary interface via React/TypeScript and Recharts.
- There is no active Streamlit entrypoint in the product runtime.

Current visual direction targets the TS UI:

- lower-case `synapse` branding
- bold gradient-backed interface with glass panels
- modern chart primitives from Recharts
- tabs labeled `reflect` and `talk`
- a stronger color system tuned for interactive visuals

### Sidebar

- sidebar shows the active prompt and session metadata
- supports dedicated chat thread IDs for context continuity

### Tab 1: Reflect

Purpose:

user writes a reflection, then submits it to `/api/reflection`.

- app shows extracted entities and generated interpretation from the existing LangGraph result
- results are rendered from API payload only (no internal module state coupling)

Rendered sections:

- patterns as metrics
- emotions as metrics
- themes as simple text
- IFS parts
- schema patterns
- people
- body signals
- insights
- follow-up questions

### Tab 2: Talk

Purpose:

- freeform conversational querying of the stored graph through the ReAct chat agent via `/api/chat`

Behavior:

- chat history is now held in frontend state, with backend thread ids for persistence
- agent memory also uses `MemorySaver`
- each frontend session should reuse the same `thread_id` for continuity
- the transcript panel stays hidden until the user sends the first question so the composer remains front-and-center

## Prompts and product tone

Prompt definitions live in [reflect/prompts.py](/Users/ian/dev/synapse/reflect/prompts.py).

There are four important prompt surfaces:

- `EXTRACTION_SYSTEM_PROMPT`
- `CHAT_SYSTEM_PROMPT`
- `INSIGHT_PROMPT`
- `FOLLOWUP_PROMPT`

The product voice is intended to be:

- warm
- non-diagnostic
- pattern-oriented
- grounded in CBT / DBT / IFS / Schema Therapy language
- specific rather than generic

If you change the therapeutic framing or product tone, update this file.

## Seed data

The sample corpus in [data/sample_reflections/](/Users/ian/dev/synapse/data/sample_reflections) is important because it is part of the product demo, not just filler.

The 18 files are deliberately split across:

- present-day work, anxiety, perfectionism, comparison, boundaries, insomnia, gratitude
- childhood and family-origin reflections about dad, mum, abandonment, shame, people-pleasing, numbing, relationship shutdown

The corpus is designed so the graph can connect present behavior to earlier roots:

- work feedback links to childhood criticism
- friendship anxiety links to abandonment by dad
- people-pleasing links to being the easy child
- numbing and shutdown link to parental conflict and emotional overwhelm
- catastrophizing links to maternal anxiety

When evaluating extraction or graph quality, seed with this corpus first.

## How to run

Use [`README.md`](/Users/ian/dev/synapse/README.md) for the canonical onboarding path:

The recommended local runner is:

- `just sync`
- `just dev` (runs backend + frontend, auto-syncs missing/stale frontend deps, and first kills any PIDs recorded in `.tmp/synapse-pids` from a previous run)
- `just telegram` (optional standalone bot runner, typically in a second terminal)
- `just dev-all` (optional combined runner for backend + frontend + Telegram in one terminal, with the same frontend dependency auto-sync)
- `just stop` (to shut down whichever services were launched by `just dev` or `just dev-all`)

### Install dependencies

Use the project package manager already implied by `uv.lock`:

```bash
uv sync
```

### Run the API server

```bash
uv run uvicorn api_server:app --reload --port 8000
```

### Run the TypeScript frontend

```bash
cd frontend
npm install
npm run dev
```

This expects the API on `http://localhost:8000`; set `VITE_API_URL` and `CORS_ORIGINS` for different host/ports.

### Run the Telegram bot

```bash
just telegram
```

This loads `.env` via `python-dotenv`; `TELEGRAM_BOT_TOKEN` must be set.
If Telegram returns a polling `409 Conflict` (another instance already polling that token), the bot now logs a single conflict message and exits cleanly instead of repeatedly dumping stack traces.

### Seed the demo graph

```bash
uv run python seed_data.py
```

### Run the trivial smoke scripts

```bash
uv run python test.py
uv run python main.py
uv run python surreal_test.py
uv run python langchain_surreal.py
```

Only `seed_data.py`, `api_server.py`, and `frontend/` are central to the production product surface.

## Observability

The repo uses `@traceable` decorators from LangSmith on:

- pipeline nodes
- extraction wrapper
- schema init
- graph CRUD/query helpers

The plan doc expects:

- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_PROJECT=synapse-hackathon`

This is observability-by-instrumentation, not a custom logging system.

## Important implementation caveats

Agents should know these before making changes.

### 1. `PLAN.md` is more ambitious than the current code

The plan is directionally right, but some statements are aspirational or simplified. Use code as the final truth.

Examples:

- The plan says the app has a polished architecture narrative; the repo is still a compact hackathon prototype.
- The plan describes broad graph semantics; the actual app mostly exposes straightforward queries and summaries.

### 2. `main.py` is not the app

[main.py](/Users/ian/dev/synapse/main.py) is just an OpenAI call used as a scratch connectivity check.

### 3. No docs for optional run flags

If you add environment-specific startup modes, document them in [`README.md`](/Users/ian/dev/synapse/README.md).

### 4. Some files are experiments / spikes

- [langchain_surreal.py](/Users/ian/dev/synapse/langchain_surreal.py)
- [surreal_test.py](/Users/ian/dev/synapse/surreal_test.py)
- [test.py](/Users/ian/dev/synapse/test.py)

Treat them as exploratory utilities unless the user asks to formalize them.

### 5. Legacy graph visualization packages

`streamlit-agraph` has been removed from runtime dependencies during TS cutover.

### 6. The app uses module-level shared state

[reflect/agent.py](/Users/ian/dev/synapse/reflect/agent.py) keeps connection, vector store, and tool lists in globals. Be careful with initialization order and side effects.

### 7. Schema init runs during app startup

`_init()` calls `init_schema(_conn)` on first use. Changes to schema setup can affect every app start and every seed run.

### 8. The graph is single-tenant in practice

There is no user partitioning on records. All reflections land in the same graph/database namespace configured in env.

### 9. Privacy / safety is not production-grade

This is reflective mental-health-adjacent software, but it does not currently implement the safeguards expected in a real deployment.

### 10. Some defined structures are not fully used

Examples visible in the current code:

- `_slug()` exists in [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py) but is unused.
- `reminds_of` is defined in schema but no creation/query logic currently uses it.
- `query_pattern_evolution()` exists, but the chat tool `get_temporal_evolution()` uses its own direct query instead.

Do not remove these casually without confirming intent.

## Guidance for future agents

When changing this repo:

- Read [PLAN.md](/Users/ian/dev/synapse/PLAN.md) for intent.
- Read this file next for current-state context.
- Then read the specific implementation files you are touching.

If the task touches ingestion or extraction:

- inspect [reflect/agent.py](/Users/ian/dev/synapse/reflect/agent.py)
- inspect [reflect/extraction.py](/Users/ian/dev/synapse/reflect/extraction.py)
- inspect [reflect/prompts.py](/Users/ian/dev/synapse/reflect/prompts.py)
- inspect [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py)

If the task touches data modeling or search:

- inspect [reflect/db.py](/Users/ian/dev/synapse/reflect/db.py)
- inspect [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py)
- remember the SurrealDB v3 patches

If the task touches the UI:

- inspect [frontend/src/App.tsx](/Users/ian/dev/synapse/frontend/src/App.tsx)
- preserve the two-tab mental model (`reflect` and `talk`) unless intentionally redesigning the product

If the task touches prompts or therapeutic framing:

- avoid diagnostic language
- keep outputs grounded in actual graph data
- preserve the warm, observational tone
- keep this file updated

If the task changes commands, env vars, schema, tabs, tools, or key flows:

- update this file in the same change

## Suggested next-doc improvements

These are not yet implemented, but they would reduce future confusion:

- document the required `.env` keys explicitly
- add a real test harness around extraction parsing and graph queries
- document expected SurrealDB version
- separate experimental scripts from product code

## Last refreshed

This file was written after reading:

- [PLAN.md](/Users/ian/dev/synapse/PLAN.md)
- [README.md](/Users/ian/dev/synapse/README.md)
- [ARCHITECTURE.md](/Users/ian/dev/synapse/ARCHITECTURE.md)
- [london-hackathon-full-details.md](/Users/ian/dev/synapse/london-hackathon-full-details.md)
- [pitch/PITCH_PLAYBOOK.md](/Users/ian/dev/synapse/pitch/PITCH_PLAYBOOK.md)
- [.claude/skills/langchain/SKILL.md](/Users/ian/dev/synapse/.claude/skills/langchain/SKILL.md)
- [.claude/skills/surrealdb/SKILL.md](/Users/ian/dev/synapse/.claude/skills/surrealdb/SKILL.md)
- [.claude/skills/vite-typescript/SKILL.md](/Users/ian/dev/synapse/.claude/skills/vite-typescript/SKILL.md)
- [.claude/skills/python/SKILL.md](/Users/ian/dev/synapse/.claude/skills/python/SKILL.md)
- [pyproject.toml](/Users/ian/dev/synapse/pyproject.toml)
- [render.yaml](/Users/ian/dev/synapse/render.yaml)
- [api_server.py](/Users/ian/dev/synapse/api_server.py)
- [main.py](/Users/ian/dev/synapse/main.py)
- [seed_data.py](/Users/ian/dev/synapse/seed_data.py)
- [langchain_surreal.py](/Users/ian/dev/synapse/langchain_surreal.py)
- [surreal_test.py](/Users/ian/dev/synapse/surreal_test.py)
- [test.py](/Users/ian/dev/synapse/test.py)
- [reflect/service.py](/Users/ian/dev/synapse/reflect/service.py)
- [reflect/auth.py](/Users/ian/dev/synapse/reflect/auth.py)
- [reflect/db.py](/Users/ian/dev/synapse/reflect/db.py)
- [reflect/graph_store.py](/Users/ian/dev/synapse/reflect/graph_store.py)
- [reflect/extraction.py](/Users/ian/dev/synapse/reflect/extraction.py)
- [reflect/agent.py](/Users/ian/dev/synapse/reflect/agent.py)
- [reflect/chat_agent.py](/Users/ian/dev/synapse/reflect/chat_agent.py)
- [reflect/prompts.py](/Users/ian/dev/synapse/reflect/prompts.py)
- [frontend/src/App.tsx](/Users/ian/dev/synapse/frontend/src/App.tsx)
- the seeded reflections under [data/sample_reflections/](/Users/ian/dev/synapse/data/sample_reflections)

If you make the codebase materially different from this description, refresh this section too.
