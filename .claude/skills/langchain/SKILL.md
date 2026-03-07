---
name: langchain
description: Build and refactor LangChain/LangGraph agent systems with reliable tool calling, state design, and prompt boundaries. Use for tasks involving chains, ReAct agents, LangGraph nodes/edges, memory, and model/tool orchestration.
---

# LangChain Skill

Use this skill when implementing or reviewing LangChain/LangGraph flows.

## When to apply

- Adding or modifying LangGraph nodes, edges, or state
- Implementing ReAct agents and tool lists
- Improving prompt boundaries and output parsing
- Debugging agent/tool failures and non-deterministic behavior
- Adding streaming behavior or thread continuity

## Workflow

1. Map the runtime path first.
- Identify entrypoint and the exact execution path.
- List state keys consumed/produced per node.

2. Make state explicit and typed.
- Keep a single typed state object per graph.
- Add defaults/fallbacks for optional values.

3. Keep tool surfaces narrow.
- Prefer small, composable tools.
- Write tool docstrings for invocation intent.
- Return machine-parsable outputs when possible.

4. Enforce output contracts.
- Use strict JSON response instructions for structured steps.
- Add graceful fallback parsing behavior.

5. Separate responsibilities.
- Retrieval/extraction/storage/synthesis should be different steps.
- Avoid hidden side effects in prompt-only logic.

6. Instrument for observability.
- Add `@traceable` on node-level and key tool wrappers.
- Verify traces include tool sequence and node timings.

## Patterns to prefer

- Deterministic graph topology with explicit handoffs
- ReAct for tool selection; direct chain calls for strict transforms
- Thread IDs passed through API boundary and normalized server-side
- Model/provider split by task type (extraction vs synthesis vs chat)

## Anti-patterns

- A monolithic prompt doing extraction + retrieval + synthesis
- Implicit state writes without schema updates
- Broad tools with hidden branching side effects
- Missing error handling for tool/model output parsing

## Validation checklist

- Graph compiles and node transitions are valid
- Each node reads only required state keys
- Structured outputs parse successfully under malformed responses
- Tool calls and model outputs appear correctly in traces
