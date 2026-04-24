# Synapse Pitch Playbook

This playbook is for two deliverables:

1. **Live on-stage demo (2:00 max)**
2. **Submission video (2:00 target)**

Use this as an execution runbook.

---

## Hackathon non-negotiables

To stay eligible and score well, we must show:

- **LangChain and/or LangGraph** for agent orchestration
- **SurrealDB** as persistent data layer
- A practical, working prototype demonstrated live
- Submission assets:
  - Public GitHub repo
  - Clear README (what it does + how to run)
  - 2-minute video overview
  - Live Sunday demo

---

## Core story (what we are selling)

Synapse is a reflection agent that **remembers in structure, not just tokens**.

Most journaling tools are stateless. Synapse turns reflections into an evolving SurrealDB graph + vector memory, then uses LangGraph and LangChain agents to reason over that history.

This is the key product claim:

**Clinically informed reflection frameworks (CBT, DBT, IFS, Schema) become durable machine-readable memory that improves answers over time.**

---

## 10-second positioning line

"We built a stateful reflection agent where LangGraph orchestrates multi-step reasoning and SurrealDB stores evolving graph + vector memory, so answers get better with history instead of resetting each session."

---

## Judge-aligned scorecard (100 points)

| Criterion | Weight | What to claim | What to visibly prove |
|---|---:|---|---|
| Structured Memory / Knowledge Usage (SurrealDB) | 30 | Typed entities + relations + vectors in one persistent store | Show extracted entities, totals/drill-down, and cross-reflection continuity |
| Agent Workflow Quality (LangChain / LangGraph) | 20 | 6-node LangGraph pipeline + ReAct agents with tools | Narrate pipeline stages and show talk answer grounded in tools |
| Persistent Agent State | 20 | MemorySaver threads + user-scoped history + cross-session context | Ask a history-dependent question and show specific recurring patterns |
| Practical Use Case | 20 | Real journaling pain point: repetitive, forgetful coaching | Show actionable pattern/person/body-signal insights |
| Observability | 10 | Traceable execution with LangSmith | Show trace screenshot/tab if available, or mention `@traceable` eval traces |

---

## High-value README insights to surface

These are differentiators judges will remember:

- **Multichannel memory:** web reflections + Telegram text + Telegram voice notes all write into the same user graph.
- **Structured therapeutic lenses:** extraction is grounded in CBT/DBT/IFS/Schema frameworks, not generic motivation.
- **Reliability guardrails:** crisis-safe prompting, non-diagnostic framing, strict JSON contracts, graceful fallback parsing.
- **Grounding architecture:** extraction agent must retrieve existing patterns + similar reflections before final extraction.
- **Evidence of rigor:** dedicated eval harness (`evals.py`) for extraction quality, graph integrity, chat grounding, and latency.
- **Observable system:** LangSmith traceability across pipeline and tools.
- **Security basics in place:** bcrypt passwords, JWT auth, user-scoped data boundaries.

---

## Live demo plan (2:00)

### Demo goal

Show one full proof loop:

`reflect -> extract -> persist -> drill down -> ask your graph`

### Stage setup (before speaking)

- Logged into demo account
- Tab 1: `reflect`
- Tab 2: `talk`
- Optional Tab 3: LangSmith trace page or screenshot
- Reflection and talk question pre-copied

### Suggested reflection text

```text
I got feedback from my manager today and immediately felt my chest tighten.
I started over-editing everything and avoided replying for hours.
It felt like if I made one mistake I'd be judged the way I was growing up.
I kept checking Slack instead of finishing the task.
```

### Suggested talk question

```text
What pattern shows up most when I mention feedback or authority figures?
```

### 2:00 run-of-show

| Time | On screen | Speaker line |
|---|---|---|
| 0:00-0:12 | `reflect` screen | "Synapse is a memory-first reflection agent: structured memory in SurrealDB, orchestrated by LangGraph." |
| 0:12-0:30 | Submit reflection | "This triggers a 6-node pipeline: store reflection, extract patterns, update graph, query history, generate insights, generate follow-ups." |
| 0:30-0:52 | Processing state | "Extraction is retrieval-grounded, so it reuses existing labels and avoids duplicate concepts over time." |
| 0:52-1:15 | Results panel | "We now get typed outputs: patterns, emotions, themes, IFS parts, schemas, people, and body signals." |
| 1:15-1:35 | Open totals drill-down | "Because memory is structured, we can inspect trend frequency and relationship impact across history." |
| 1:35-1:53 | `talk` question and answer | "The chat agent uses graph + semantic tools to answer from stored context, not just this one prompt." |
| 1:53-2:00 | Final frame | "This is the hackathon thesis: reliable agents through structured, persistent, observable memory." |

---

## Tight live script (readable version)

"Most reflection AI is stateless, so it forgets your patterns. Synapse fixes that by combining LangGraph orchestration with SurrealDB graph + vector memory.

When I submit a reflection, we run a 6-step agent workflow: persist the entry, extract structured signals, update the graph, query prior context, then synthesize insights and follow-up prompts.

The extraction step is tool-grounded: it checks existing patterns and similar reflections first, so memory stays consistent over time.

Now we can see typed outputs across therapeutic lenses: patterns, emotions, IFS parts, schema patterns, people, and body signals.

In Talk, the agent answers with graph tools and semantic retrieval over historical context, so responses are grounded in this user's evolving memory.

We also instrument this with LangSmith and evaluate extraction quality, graph integrity, grounding, and latency. So Synapse is not just a chatbot demo. It is a practical, stateful, observable agent system."

---

## Fallback plan (latency-safe)

If reflection processing is slow:

1. Use already-processed reflections in the same account.
2. Continue with drill-down and `talk` to prove persistent memory.
3. State: "Fresh processing typically completes in ~15-30s; this view is from the same pipeline and memory graph."

If talk response is slow:

1. Keep the question visible.
2. Narrate the tool path (overview + deep-dive + hybrid search).
3. Show a prior answer in the same thread to prove grounding.

---

## Submission video plan (2:00)

### Shot list

| Time | Visual | Voiceover |
|---|---|---|
| 0:00-0:08 | Title card | "Synapse turns journaling into evolving structured memory." |
| 0:08-0:24 | Reflect UI | "LangGraph orchestrates a multi-step workflow over SurrealDB memory." |
| 0:24-0:50 | Submit reflection | "We extract clinically grounded signals, persist graph state, and generate personalized insights." |
| 0:50-1:15 | Output + drill-down | "Insights are inspectable: trends, triggers, and relationship dynamics." |
| 1:15-1:40 | Talk answer | "ReAct tools query graph + vectors for grounded history-aware responses." |
| 1:40-1:52 | LangSmith/evals slate | "Execution is observable and tested across quality, grounding, and latency." |
| 1:52-2:00 | Close card | "Stateful agents are more reliable when memory is structured and persistent." |

### Recording checklist

- 1080p, readable zoom (110-125%)
- Keep cursor movement deliberate
- Remove unrelated tabs/notifications
- Trim dead latency waits
- Keep final export under 2:00

---

## Surrealist query reference (demo appendix)

Use this block during rehearsal or live demo troubleshooting.

### 1) Discover user cohorts

```sql
SELECT
  type::record(user_id) AS id,
  user_id,
  reflections
FROM (
  SELECT user_id, count() AS reflections
  FROM reflection
  GROUP BY user_id
)
ORDER BY reflections DESC;
```

Use this to find the heaviest cohort quickly. In Surrealist graph mode, select one returned row (it now includes a concrete `id`) before moving to query 2/3/4 for linked graph views.

### 2) Reflection graph (all users)

```sql
SELECT
  id,
  created_at,
  ->reveals->pattern.* AS patterns,
  ->activates->ifs_part.* AS ifs_parts,
  ->triggers_schema->schema_pattern.* AS schemas,
  ->expresses->emotion.* AS emotions,
  ->about->theme.* AS themes,
  ->mentions->person.* AS people,
  ->feels_in_body->body_signal.* AS body_signals
FROM reflection
LIMIT 8
FETCH reveals, activates, triggers_schema, expresses, about, mentions, feels_in_body;
```

### 3) Reflection graph (single user example)

```sql
LET $uid = "app_user:your_user_record_id";

SELECT
  id,
  created_at,
  ->reveals->pattern.* AS patterns,
  ->activates->ifs_part.* AS ifs_parts,
  ->triggers_schema->schema_pattern.* AS schemas,
  ->expresses->emotion.* AS emotions,
  ->about->theme.* AS themes,
  ->mentions->person.* AS people
FROM reflection
WHERE user_id = $uid
LIMIT 12
FETCH reveals, activates, triggers_schema, expresses, about, mentions;
```

### 4) Reflection graph (seed/demo rows with `user_id = NONE`)

```sql
SELECT
  id,
  created_at,
  ->reveals->pattern.* AS patterns,
  ->activates->ifs_part.* AS ifs_parts,
  ->triggers_schema->schema_pattern.* AS schemas,
  ->expresses->emotion.* AS emotions,
  ->about->theme.* AS themes,
  ->mentions->person.* AS people
FROM reflection
WHERE user_id = NONE
LIMIT 12
FETCH reveals, activates, triggers_schema, expresses, about, mentions;
```

### 5) People hub

```sql
SELECT
  id,
  name,
  relationship,
  occurrences,
  ->triggers_pattern->pattern.* AS triggered_patterns,
  <-mentions<-reflection.* AS reflections
FROM person
LIMIT 20
FETCH triggers_pattern, mentions;
```

### 6) Single-person deep dive

```sql
SELECT
  id,
  name,
  relationship,
  <-mentions<-reflection.* AS reflections,
  ->triggers_pattern->pattern.* AS triggered_patterns
FROM person
WHERE name = "Dad"
LIMIT 1
FETCH mentions, triggers_pattern, reveals, expresses, about;
```

### 7) Pattern co-occurrence network

```sql
SELECT
  id,
  name,
  category,
  occurrences,
  ->co_occurs_with->pattern.* AS co_out,
  <-co_occurs_with<-pattern.* AS co_in
FROM pattern
LIMIT 20
FETCH co_occurs_with;
```

### 8) Emotion trigger map

```sql
SELECT
  id,
  name,
  valence,
  intensity,
  ->triggered_by->theme.* AS triggers
FROM emotion
LIMIT 20
FETCH triggered_by;
```

### 9) Schema + IFS protection chain

```sql
SELECT
  id,
  name,
  domain,
  coping_style,
  <-triggers_schema<-reflection.* AS source_reflections,
  <-protects_against<-ifs_part.* AS protecting_parts
FROM schema_pattern
LIMIT 20
FETCH triggers_schema, protects_against;
```

### 10) Edge-only graph views

```sql
SELECT * FROM reveals LIMIT 120 FETCH in, out;
SELECT * FROM co_occurs_with LIMIT 120 FETCH in, out;
SELECT * FROM triggers_pattern LIMIT 120 FETCH in, out;
SELECT * FROM mentions LIMIT 120 FETCH in, out;
SELECT * FROM activates LIMIT 120 FETCH in, out;
SELECT * FROM triggers_schema LIMIT 120 FETCH in, out;
```

### Suggested run order (2-minute demo)

1. Reflection graph (#2)
2. People hub (#5)
3. Pattern network (#7)
4. Emotion trigger map (#8)
5. Schema + IFS chain (#9)
6. Edge-only view (#10)

---

## Bonus consideration (open-source contribution)

Hackathon judges will positively recognize reusable LangChain integrations published as a separate repo.

If time permits, propose one extraction from Synapse into an OSS mini-repo:

- SurrealDB graph-memory toolkit helpers
- Reflection-memory retriever adapter
- Checkpoint/state utility for LangGraph + SurrealDB

Even a focused, documented MVP can strengthen final judging.

---

## Final pre-submit checklist

- Public GitHub repo is up and accessible
- README is clear and current
- 2-minute video link prepared
- Live demo flow rehearsed with fallback
- One-line value proposition memorized
