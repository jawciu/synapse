# Synapse: Architecture & Implementation

## What It Is

A self-reflection journaling app that uses **knowledge graphs + vector embeddings** to find deep psychological patterns across journal entries — drawing from four therapy frameworks (CBT, DBT, Internal Family Systems, Schema Therapy). Built for the LangChain x SurrealDB hackathon.

**Rubric priority:** Knowledge Graph/SurrealDB 30% > Agent Workflow 20% = Persistent State 20% > Use Case 20% > Observability 10%.

---

## Stack

- **LangChain + LangGraph** — orchestrates the AI pipeline
- **SurrealDB v3 Cloud** — graph database + vector store (stores both structured relationships AND semantic embeddings)
- **OpenAI** — GPT-4o for analysis, text-embedding-3-small for embeddings (1536 dims)
- **Vite + TypeScript React** — frontend with 3 tabs
- **LangSmith** — tracing/observability on all nodes
- **Recharts** — pattern visualization charts

---

## File Structure

```
langchain-hackathon/
├── pyproject.toml
├── .env                      # SURREAL_URL/NS/DB/USER/PASS, OPENAI_API_KEY, LANGSMITH keys
├── seed_data.py              # Seeds 18 demo reflections through the full pipeline
├── reflect/
│   ├── __init__.py
│   ├── db.py                 # SurrealDB connection, schema definitions, v3 HNSW patches
│   ├── graph_store.py        # Graph CRUD, SurrealQL traversals, 14 agent tools, hybrid search
│   ├── prompts.py            # Therapy framework prompts (CBT/DBT/IFS/Schema), daily prompts
│   ├── extraction.py         # Agentic RAG extraction (retrieves context before extracting)
│   ├── agent.py              # LangGraph 6-node StateGraph pipeline
│   ├── chat_agent.py         # ReAct chat agent for "Ask your graph"
│   └── service.py            # API service helpers used by FastAPI endpoints
└── data/
    └── sample_reflections/   # 18 .txt files (10 present-day + 8 childhood/family backstory)
```

---

## SurrealDB Knowledge Graph Schema

### Node Tables

```sql
-- Core nodes
reflection    (text, created_at, daily_prompt)
pattern       (name, category, description, occurrences, embedding[1536])
theme         (name, description, embedding[1536])
emotion       (name, valence, intensity)

-- Therapy framework nodes
ifs_part       (name, role[exile|manager|firefighter], description, occurrences, embedding[1536])
schema_pattern (name, domain, coping_style, description, occurrences, embedding[1536])

-- Relationship nodes
person        (name, relationship[parent|sibling|partner|friend|colleague|authority|therapist|other], description, occurrences, embedding[1536])
body_signal   (name, location[chest|stomach|throat|head|face|etc], occurrences)
```

### Edge Relations

```sql
-- Core edges
reveals          reflection -> pattern      (strength: float)
expresses        reflection -> emotion      (intensity: float)
about            reflection -> theme
co_occurs_with   pattern -> pattern         (count: int)
triggered_by     emotion -> theme

-- IFS + Schema edges
activates        reflection -> ifs_part
triggers_schema  reflection -> schema_pattern
protects_against ifs_part -> schema_pattern

-- People + somatic edges
mentions         reflection -> person
triggers_pattern person -> pattern
reminds_of       person -> person           (description: string)
feels_in_body    reflection -> body_signal
```

### HNSW Vector Indexes

All node tables with embeddings have HNSW indexes for KNN search:
```sql
DEFINE INDEX pattern_embedding_idx ON pattern FIELDS embedding HNSW DIMENSION 1536 DIST COSINE TYPE F32;
DEFINE INDEX ifs_part_embedding_idx ON ifs_part FIELDS embedding HNSW DIMENSION 1536 DIST COSINE TYPE F32;
DEFINE INDEX schema_pattern_embedding_idx ON schema_pattern FIELDS embedding HNSW DIMENSION 1536 DIST COSINE TYPE F32;
DEFINE INDEX person_embedding_idx ON person FIELDS embedding HNSW DIMENSION 1536 DIST COSINE TYPE F32;
DEFINE INDEX theme_embedding_idx ON theme FIELDS embedding HNSW DIMENSION 1536 DIST COSINE TYPE F32;
```

Plus the `documents` table (managed by langchain-surrealdb) for reflection text vector search.

---

## Two Agents

### Agent 1: Extraction Agent (Agentic RAG)

Runs during step 2 of the pipeline. A ReAct agent that retrieves context BEFORE extracting patterns.

**Tools (2):**
- `get_existing_patterns` — queries all pattern nodes from SurrealDB to reuse names
- `retrieve_similar_reflections` — vector KNN search for past reflections with similar themes

**Why agentic:** Without retrieval, the LLM creates `"catastrophizing"` in one session and `"catastrophic thinking"` in another. By fetching existing patterns first, it reuses names and keeps the graph coherent.

**Extraction categories:**
- CBT cognitive distortions (all-or-nothing, catastrophizing, mind-reading, etc.)
- DBT emotional patterns (intensity, triggers, window of tolerance)
- Relational patterns (anxious seeking, avoidant withdrawal, people-pleasing)
- Behavioral patterns (avoidance, procrastination, self-sabotage)
- IFS parts (exiles, managers, firefighters, Self-energy vs blending)
- Schema Therapy (18 early maladaptive schemas across 5 domains + 3 coping styles)
- People mentioned (with relationship type)
- Body signals / somatic markers (with body location)

**Output format (JSON):**
```json
{
  "patterns": [{"name": "...", "category": "cognitive|emotional|relational|behavioral", "description": "...", "strength": 0.0-1.0}],
  "emotions": [{"name": "...", "valence": "positive|negative|neutral", "intensity": 0.0-1.0}],
  "themes": [{"name": "...", "description": "..."}],
  "ifs_parts": [{"name": "...", "role": "exile|manager|firefighter", "description": "..."}],
  "schemas": [{"name": "...", "domain": "disconnection|impaired_autonomy|...", "coping_style": "surrender|avoidance|overcompensation|none", "description": "..."}],
  "people": [{"name": "...", "relationship": "parent|friend|...", "description": "..."}],
  "body_signals": [{"name": "...", "location": "chest|face|..."}]
}
```

### Agent 2: Chat Agent (14 tools)

ReAct agent with memory for the "Ask" tab. Decides which tools to call based on the user's question.

**Tools:**
| Tool | What it does | When to use |
|------|-------------|-------------|
| `hybrid_graph_search` | Semantic search across ALL node types + graph traversal | Broad/vague questions |
| `get_all_patterns_overview` | All patterns by frequency + co-occurrences | "What patterns do I repeat?" |
| `get_all_emotions_overview` | Emotions + negative triggers | "What emotions come up most?" |
| `get_ifs_parts_overview` | IFS parts with source reflections | "What inner parts do I have?" |
| `get_schemas_overview` | Schemas with source reflections | "What drives my behavior?" |
| `get_people_overview` | People + patterns they trigger | "Who triggers my patterns?" |
| `get_person_deep_dive` | Deep analysis of one person | "Tell me about my dad" |
| `get_body_signals_overview` | Somatic markers | "What does my body tell me?" |
| `get_deep_pattern_analysis` | Single pattern with IFS/schema/people links | "Why do I people-please?" |
| `get_graph_summary` | High-level counts and connections | General questions |
| `get_emotion_triggers` | Theme → emotion traversal | "What triggers my anxiety?" |
| `get_pattern_connections` | Co-occurring patterns + reflections | "What goes with perfectionism?" |
| `get_temporal_evolution` | Pattern over time | "How has avoidance changed?" |
| `semantic_search_reflections` | Vector search on reflection text | Finding related journal entries |

---

## LangGraph Pipeline (6 nodes)

```
Journal Entry
     │
     ▼
┌─────────────────┐
│ 1. STORE         │  Save to SurrealDB + vector embedding in documents table
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. EXTRACT       │  Agentic RAG — retrieves existing patterns + similar
│                   │  reflections, then extracts patterns, emotions, themes,
│                   │  IFS parts, schemas, people, body signals
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. UPDATE GRAPH  │  Upsert all nodes (with embeddings) + create all edges
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. QUERY GRAPH   │  Multi-hop traversals: co-occurrences, triggers, centrality
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. INSIGHTS      │  LLM generates IFS/Schema-informed insights using
│                   │  current extraction + historical graph data
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. FOLLOW-UPS    │  Targeted questions about relationships, body awareness,
│                   │  inner part ages, unmet needs
└─────────────────┘
```

**Checkpointing:** `MemorySaver` with per-reflection thread IDs.

---

## Hybrid Search: Vector + Graph

Every graph node (pattern, IFS part, schema, person, theme) stores a 1536-dim embedding of its description. This enables:

1. **Semantic graph search** — "why do I shut down?" finds `numbing part` (firefighter), `avoidance` (pattern), and `emotional inhibition` (schema) by meaning
2. **Multi-hop semantic queries** — find nodes by meaning → traverse edges → discover connected patterns
3. **Better deduplication** — similar embeddings catch near-duplicate node names

The `hybrid_graph_search` tool searches across ALL node types simultaneously, then follows graph edges for context.

---

## Frontend UI

**Sidebar:** Daily reflection prompt (random) + "Use This Prompt" button

**Tab 1 — Reflect:**
- Text area for journal entry
- After submit: 3-column display of patterns/emotions/themes
- IFS parts + Schema patterns section
- People + Body signals section
- Insights paragraph
- 3 follow-up questions

**Tab 2 — Patterns:**
- Top 5 per category (cognitive, emotional, relational, behavioral) chart panels
- IFS and schema summaries
- Pattern and emotion charting
- People and body signal summaries
- People in reflections with relationship types
- Body signals with location

**Tab 3 — Ask:**
- Chat interface with the 14-tool ReAct agent
- Memory across the conversation session

---

## Seed Data

18 sample reflections designed to build a rich, interconnected graph:

**Present-day (1-10):** work stress, friendship fears, morning routine, perfectionism, Sunday anxiety, comparison, boundaries, progress, insomnia, gratitude

**Childhood/backstory (11-18):** childhood criticism from dad, inherited anxiety from mum, dad leaving at 11, being the "easy child", inner critic as dad's voice, numbing/dissociation pattern, shame spirals, emotional shutdown in relationships

The backstory reflections deliberately reference events from entries 1-10, so the graph builds cross-connections between present patterns and their childhood origins.

---

## LangSmith Tracing

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=synapse-hackathon
```

All 6 pipeline nodes + all graph store functions decorated with `@traceable`. Auto-traces LangGraph nodes + LLM calls.

---

## Key SurrealQL Queries

```sql
-- Full journey: reflection → patterns → IFS parts → schemas
SELECT
    text AS reflection,
    ->reveals->pattern.name AS patterns,
    ->activates->ifs_part.name AS ifs_parts,
    ->triggers_schema->schema_pattern.name AS schemas,
    ->expresses->emotion.name AS emotions
FROM reflection LIMIT 5;

-- IFS parts protecting against schemas
SELECT in.name AS part, in.role AS role, out.name AS schema, out.domain AS domain
FROM protects_against;

-- What patterns does a specific person trigger?
SELECT ->triggers_pattern->pattern.name AS patterns
FROM person WHERE name = 'dad';

-- Hybrid vector + graph: semantic search then traverse
SELECT name, category, description, vector::distance::knn() AS dist
FROM pattern WHERE embedding <|3,COSINE|> $query_vector
ORDER BY dist;

-- Pattern co-occurrence
SELECT in.name AS pattern_a, out.name AS pattern_b, count AS times
FROM co_occurs_with ORDER BY times DESC LIMIT 10;

-- Negative emotion triggers (2-hop)
SELECT in.name AS emotion, out.name AS theme
FROM triggered_by WHERE in.valence = 'negative';

-- Most connected patterns (centrality)
SELECT name, category, occurrences,
       array::len(->co_occurs_with) + array::len(<-co_occurs_with) AS connections
FROM pattern ORDER BY connections DESC LIMIT 5;
```

---

## What's Implemented (all done)

- [x] Text input → stored reflection in SurrealDB with vector embedding
- [x] LangGraph 6-node pipeline runs end-to-end
- [x] Agentic extraction: LLM retrieves existing patterns before extracting
- [x] Pattern/emotion/theme/IFS part/schema/person/body signal graph nodes + edges
- [x] Vector embeddings on all graph nodes with HNSW indexes
- [x] Hybrid vector + graph search across all node types
- [x] 7+ SurrealQL graph traversal queries (multi-hop, co-occurrence, temporal, triggers)
- [x] IFS parts (exiles, managers, firefighters) detection and storage
- [x] Schema Therapy (18 schemas, 5 domains, 3 coping styles) detection
- [x] People/relationship tracking with pattern trigger links
- [x] Body signal / somatic marker tracking
- [x] Insights with IFS/Schema-informed language
- [x] Follow-up questions targeting relationships, body awareness, unmet needs
- [x] Chat agent with 14 tools including hybrid graph search
- [x] Visual dashboard with per-category pattern charts
- [x] LangSmith traces on all nodes and tools
- [x] 18 pre-seeded reflections (present-day + childhood backstory)
