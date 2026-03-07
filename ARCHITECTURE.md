# Synapse — Architecture Overview

## Two Scenarios

Synapse has two distinct agent flows: one for **processing reflections** and one for **answering questions**.

---

## Scenario 1: User Submits a Reflection

A deterministic 6-node LangGraph pipeline with parallel entry points.

```
                         +---------------------------+
                         |       User writes a       |
                         |     reflection entry      |
                         +------------+--------------+
                                      |
                          +-----------+-----------+
                          |                       |
                          v                       v
                 +--------+--------+    +---------+---------+
                 | store_reflection |    | extract_patterns  |
                 |    (~0.2s)      |    |    (~12s)         |
                 |                 |    |                   |
                 | - Store text in |    | AGENTIC RAG LOOP: |
                 |   SurrealDB    |    |                   |
                 | - Embed full   |    | 1. LLM decides    |
                 |   text into    |    |    which tools     |
                 |   vector store |    |    to call         |
                 +--------+--------+    | 2. Tools search   |
                          |            |    existing DB     |
                          |            |    for matches     |
                          |            | 3. LLM extracts    |
                          |            |    with context    |
                          |            +---------+---------+
                          |                      |
                          +----------+-----------+
                                     |
                          WAITS FOR BOTH
                                     |
                                     v
                          +----------+----------+
                          |    update_graph      |
                          |      (~0.5s)         |
                          |                      |
                          | - Upsert patterns,   |
                          |   emotions, themes,  |
                          |   IFS parts, schemas,|
                          |   people, body signals|
                          | - Create edges        |
                          | - Generate embeddings |
                          |   for all nodes       |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |    query_graph       |
                          |      (~0.3s)         |
                          |                      |
                          | - Co-occurrences     |
                          | - Negative triggers  |
                          | - Central patterns   |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |  generate_insights   |
                          |      (~4s)           |
                          |                      |
                          | LLM synthesizes:     |
                          | - Extracted data     |
                          | - Graph connections  |
                          | - IFS/Schema lens    |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |  generate_followups  |
                          |      (~3s)           |
                          |                      |
                          | LLM generates        |
                          | therapeutic follow-up|
                          | questions based on   |
                          | patterns + insights  |
                          +----------+----------+
                                     |
                                     v
                          +----------+----------+
                          |   Response to user:  |
                          |   - Insights text    |
                          |   - Follow-up Qs     |
                          |   - Extracted data   |
                          +---------------------+
```

### What the Extraction Agent Does (the ~12s)

This is the "agentic" part of Agentic RAG — the agent doesn't extract blindly,
it retrieves existing data first to avoid duplicates and build connections.

```
   LLM Call #1                Tool Execution              LLM Call #2              Tool Execution           LLM Call #3
  +-----------+            +----------------+           +-----------+           +----------------+        +-----------+
  |           |            |                |           |           |           |                |        |           |
  | "I should | ---------> | search_existing| --------> | "Found    | -------> | get_all_       | -----> | Now I have|
  |  check    |            | _patterns()    |           |  similar  |          |  patterns()    |        | context,  |
  |  what     |            |                |           |  ones,    |          |                |        | here's my |
  |  exists   |            | search_similar_|           |  let me   |          |                |        | structured|
  |  first"   |            | reflections()  |           |  check    |          |                |        | JSON      |
  |           |            |                |           |  the full |          |                |        | output    |
  +-----------+            +----------------+           |  list"    |          +----------------+        +-----------+
                                                        +-----------+
    ~3-4s                     ~0.5s                        ~3-4s                   ~0.5s                    ~3-4s
```

### What Gets Extracted

| Category       | Examples                                        |
|----------------|-------------------------------------------------|
| Patterns       | perfectionism, fear of abandonment, avoidance   |
| Emotions       | anxiety (negative, 0.8), pride (positive, 0.6)  |
| Themes         | work stress, family dynamics                    |
| IFS Parts      | inner critic (manager), wounded child (exile)   |
| Schemas        | abandonment/instability, unrelenting standards  |
| People         | Dad, Mum, Jake, Boss                            |
| Body Signals   | tight chest, racing heart, stomach knot         |

---

## Scenario 2: User Asks a Question

A single ReAct agent with 14 tools. No fixed pipeline — the agent decides what to look up.

```
                         +---------------------------+
                         |    User asks a question   |
                         | "How does my relationship |
                         |  with dad affect me?"     |
                         +------------+--------------+
                                      |
                                      v
                          +-----------+-----------+
                          |    ReAct Chat Agent    |
                          |    (GPT-4o + tools)    |
                          +-----------+-----------+
                                      |
                    +-----------------+-----------------+
                    |                                   |
                    v                                   v
            LLM decides                          LLM decides
            tool call #1                         tool call #2 (if needed)
                    |                                   |
         +----------+----------+             +----------+----------+
         | get_person_deep_dive|             | hybrid_graph_search |
         |    ("Dad")          |             |  ("dad patterns")   |
         +----------+----------+             +----------+----------+
                    |                                   |
                    v                                   v
          Dad mentioned in 5                  Vector matches across
          reflections, linked                 pattern + schema +
          to: fear of criticism,              person tables
          emotional shutdown
                    |                                   |
                    +-----------------+-----------------+
                                      |
                                      v
                          +-----------+-----------+
                          |  LLM generates final   |
                          |  answer grounded in    |
                          |  real graph data       |
                          +-----------+-----------+
                                      |
                                      v
                          +-----------+-----------+
                          | "Your dad appears in 5 |
                          |  reflections, often    |
                          |  linked to fear of     |
                          |  criticism and          |
                          |  emotional shutdown..." |
                          +------------------------+
```

### The 14 Chat Tools

The agent picks from these based on the question:

| Tool                        | What it does                                              |
|-----------------------------|-----------------------------------------------------------|
| `get_all_patterns`          | List all patterns with occurrence counts                  |
| `get_pattern_detail`        | Deep dive on one pattern — reflections, co-occurrences    |
| `get_central_patterns`      | Most connected patterns in the graph                      |
| `get_co_occurrences`        | Patterns that appear together frequently                  |
| `get_negative_triggers`     | Themes that trigger negative emotions                     |
| `get_emotions_overview`     | All tracked emotions with valence                         |
| `get_ifs_parts_overview`    | All IFS parts — exiles, managers, firefighters            |
| `get_schemas_overview`      | Schema therapy patterns with domains and coping styles    |
| `get_deep_pattern_analysis` | Full graph traversal from a pattern through all edges     |
| `get_people_overview`       | All people mentioned, with relationship types             |
| `get_person_deep_dive`      | One person's full impact — patterns, emotions, reflections|
| `get_body_signals_overview` | Somatic markers and their frequencies                     |
| `search_similar_reflections`| Vector similarity search across past reflections          |
| `hybrid_graph_search`       | KNN search across ALL node types simultaneously           |

### Example Tool Chains by Question Type

```
"What's my most common pattern?"
  -> get_all_patterns -> answer                                    (~3s)

"How does my relationship with dad affect me?"
  -> get_person_deep_dive("Dad") -> hybrid_graph_search("dad") -> answer   (~6s)

"Do I have any patterns related to gambling?"
  -> hybrid_graph_search("gambling") -> answer (nothing found)     (~3s)

"What are my IFS parts?"
  -> get_ifs_parts_overview -> get_schemas_overview -> answer       (~5s)

"When do I feel tightness in my chest?"
  -> get_body_signals_overview -> search_similar_reflections -> answer  (~5s)
```

---

## The Knowledge Graph (SurrealDB)

All data lives in a graph database with typed nodes and edges:

```
                                    +-------------+
                          +-------->|   theme     |
                          | about   +-------------+
                          |
+-------------+  reveals  +-------------+  co_occurs_with  +-------------+
| reflection  |---------->|   pattern   |<----------------->|   pattern   |
+-------------+           +-------------+                   +-------------+
       |                        ^
       | expresses              | triggers_pattern
       v                        |
+-------------+           +-------------+
|  emotion    |           |   person    |
+-------------+           +-------------+
       |                        ^
       | triggered_by           | mentions
       v                        |
+-------------+           +-------------+
|   theme     |           | reflection  |
+-------------+           +-------------+

+-------------+  activates   +-------------+  protects_against  +-----------------+
| reflection  |------------->|  ifs_part   |------------------->| schema_pattern  |
+-------------+              +-------------+                    +-----------------+
       |                                                              ^
       | triggers_schema                                              |
       +--------------------------------------------------------------+

+-------------+  feels_in_body  +-------------+
| reflection  |---------------->| body_signal |
+-------------+                 +-------------+
```

### Hybrid Search

Every node (pattern, IFS part, schema, person, theme) has a **vector embedding** stored alongside it. This enables:

- **Graph traversal**: follow edges to find connections (e.g., pattern -> co_occurs_with -> pattern)
- **Vector similarity**: KNN search across all node types at once (e.g., "abandonment" finds the pattern, the schema, and related IFS parts)
- **Combined**: the chat agent uses both — graph tools for structured queries, hybrid_graph_search for fuzzy/semantic queries

---

## Tech Stack

| Layer          | Technology                              |
|----------------|-----------------------------------------|
| Orchestration  | LangGraph (StateGraph + ReAct agents)   |
| LLM            | GPT-4o (via LangChain)                  |
| Embeddings     | OpenAI text-embedding-3-small (1536d)   |
| Database       | SurrealDB v3 Cloud (graph + vector)     |
| Vector Index   | HNSW (cosine similarity)                |
| Observability  | LangSmith (@traceable on every node)    |
