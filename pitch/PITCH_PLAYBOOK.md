# Synapse Pitch Playbook

This playbook is for two deliverables:

1. **Live on-stage demo (2:00 max)**
2. **Submission video (2:00 target)**

Use this exactly as a runbook.

---

## Core story (what we are selling)

Synapse is a reflective AI that **remembers in structure, not just tokens**.

Most journaling agents are single-turn and forgetful. Synapse stores durable, queryable memory in SurrealDB (graph + vectors), then uses LangGraph/LangChain agents to reason across that evolving context.

The result is not "generic coaching." It is context-grounded insight tied to recurring patterns, people, and body signals over time.

---

## 10-second positioning line

"We built a stateful reflection agent where LangGraph runs the workflow and SurrealDB acts as long-term memory, so answers improve with history instead of resetting every session."

---

## Judge-aligned message map

- **Structured memory (30%)**: typed graph entities + edges + vector search in SurrealDB
- **Agent workflow (20%)**: multi-step LangGraph pipeline + ReAct chat agent with tools
- **Persistent state (20%)**: user-scoped history, MemorySaver threads, cross-session continuity
- **Practical use case (20%)**: real reflective journaling and pattern awareness
- **Observability (10%)**: LangSmith traceable nodes and tool calls

---

## Live demo plan (2:00)

### Demo goal

Show one complete loop: ingest -> persist -> analyze -> query.

### Stage setup (before speaking)

- App already open at `http://localhost:5173`, logged into demo account
- Browser tab 1: `reflect`
- Browser tab 2 ready (or quick toggle): totals drill-down and `talk` tab
- Reflection text pre-pasted in clipboard
- One fallback question pre-copied for `talk`
- Terminal running `just dev`

### Suggested reflection text (paste-ready)

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
| 0:00-0:12 | Synapse home (`reflect`) | "Synapse is a memory-first reflection agent. It does not just answer, it builds a persistent knowledge graph of your patterns." |
| 0:12-0:28 | Paste reflection, click `reflect` | "When I submit a reflection, LangGraph runs our multi-step pipeline: extraction, graph updates, historical query, then personalized insight generation." |
| 0:28-0:52 | While processing, describe architecture | "The key is SurrealDB as both graph and vector memory. So the agent can reuse existing pattern labels and connect this reflection to prior context." |
| 0:52-1:15 | Show extracted results + insights + follow-ups | "Now we get structured outputs: patterns, emotions, themes, people, body signals, and follow-up questions grounded in my history." |
| 1:15-1:35 | Open `people` or `patterns` drill-down | "This is not static text. We can inspect relationship impact and pattern frequency from the persisted graph." |
| 1:35-1:55 | Switch to `talk`, ask prepared question | "Then the chat agent uses graph tools plus hybrid semantic search to answer from stored data, not from a blank context window." |
| 1:55-2:00 | Close on value statement | "That is Synapse: reliable agent behavior through structured, evolving memory." |

---

## Live demo fallback path (if latency hits)

If reflection processing is slow on stage:

1. Use pre-existing reflection results already visible in the session.
2. Continue with drill-down + `talk` (these still prove persistent memory and agent tooling).
3. Say: "Pipeline normally completes in ~20-30s, but the graph state shown here is from the same workflow."

If chat response is slow:

1. Keep the question visible.
2. Narrate tool strategy (person deep dive + hybrid search).
3. Show previously answered message in the thread as evidence of grounded responses.

---

## Full live script (readable version)

"Synapse is a memory-first reflection agent. Most journaling AI tools are single-turn, so they forget context and repeat generic advice. We built this on LangGraph and SurrealDB so memory is durable and structured.

Here I submit a real reflection. This triggers our LangGraph pipeline: we extract patterns with tool calls, update a SurrealDB knowledge graph, query historical links, then generate insights and follow-up questions.

The important part is retrieval before extraction, so we reuse existing pattern labels instead of inventing new duplicates. That gives us consistency across time.

Now you can see structured outputs: patterns, emotions, themes, people, and body signals. These are persisted, so we can drill into relationship impact and recurring triggers.

In the talk tab, I ask a question. The chat agent calls graph tools and hybrid semantic search, then answers from stored user history.

So Synapse moves beyond a demo chatbot. It is a stateful agent system with evolving memory, grounded reasoning, and a practical user workflow."

---

## Submission video plan (2:00)

### Video objective

Deliver the same proof as live demo, but cleaner and tighter with cuts.

### Shot list + narration timing

| Time | Visual | Voiceover |
|---|---|---|
| 0:00-0:08 | Title card: "Synapse - Memory-First Reflection Agent" | "Synapse turns journaling into an evolving knowledge graph." |
| 0:08-0:22 | UI overview: totals + tabs | "Instead of one-off outputs, our agent keeps structured memory in SurrealDB." |
| 0:22-0:45 | Paste reflection and submit | "A LangGraph pipeline extracts patterns, updates graph state, and synthesizes personalized insights." |
| 0:45-1:05 | Show extracted entities + insights | "Extraction is retrieval-grounded, so labels stay consistent over time." |
| 1:05-1:25 | Show patterns/people drill-down | "Because memory is structured, we can inspect recurring triggers and relationship dynamics." |
| 1:25-1:45 | Ask question in `talk` and show response streaming | "Our ReAct chat agent answers with graph tools and hybrid semantic search." |
| 1:45-1:56 | Quick architecture slate (LangGraph + SurrealDB + LangSmith) | "This combines orchestration, persistent memory, and observability." |
| 1:56-2:00 | Closing card | "Synapse: reliable agent behavior through structured, persistent context." |

### Recording checklist

- Use 1080p capture (30fps is fine)
- Increase browser zoom to 110-125% for readability
- Keep cursor movement intentional and slow
- Hide bookmarks/tabs unrelated to demo
- Mute notifications
- Record one clean take per segment, then stitch

### Editing checklist

- Keep total duration under 2:00
- Add captions for key claims ("LangGraph pipeline", "SurrealDB graph + vector memory", "Tool-grounded answers")
- Cut dead wait time during model latency
- Ensure final export audio is normalized and clear

---

## What to show (do not skip)

- Reflection ingestion action (`reflect` submit)
- Structured extraction output
- At least one persisted analytics/drill-down panel (`people` or `patterns`)
- One `talk` question answered from memory
- Final architecture/value framing

If all five are visible, the pitch lands.

---

## Final submission checklist

- Public GitHub repo
- README that explains value + architecture + run instructions
- 2-minute project video link
- Team ready for live demo flow above
