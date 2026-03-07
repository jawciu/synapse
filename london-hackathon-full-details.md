# LONDON Hackathon: Agents & Knowledge Graphs

## LangChain x SurrealDB

We are officially one week away from the London Hackathon, and we're excited to see what you build.

This is a build-focused weekend.

The goal is simple: ship a working prototype and demo it live on Sunday.

It does not need to be polished.

It must be functional, clear, and solve a meaningful problem.

---

## The stack (required)

This is a LangChain x SurrealDB hackathon.

To be eligible for judging, your project must use:

- LangChain and/or LangGraph for agent orchestration
- SurrealDB as your persistent data layer

Knowledge graphs are a major focus, but you are not limited to graph-only designs. SurrealDB can be used for graph, relational, or hybrid models.

Strong projects will demonstrate how structured, persistent context improves agent reliability.

---

## What you are building

We are exploring how agents move beyond simple demos by grounding themselves in structured memory and state.

Your project should aim to demonstrate:

- Agentic workflows using LangChain / LangGraph
- Persistent or evolving context stored in SurrealDB
- Multi-step reasoning or stateful logic
- A practical, real-world use case

You may also explore:

- Retrieval + graph hybrids
- Tool integrations
- Custom memory implementations
- Checkpointing logic
- Embeddings or vector search

Knowledge graph usage will score highly, but creative structured memory approaches are welcome.

---

## Bonus incentive: Open-source contribution

We strongly encourage teams to publish reusable LangChain integrations as standalone open-source repositories (separate from your project repo).

Examples:

- Custom chat memory integrations
- SurrealDB toolkits or connectors
- Checkpoint integrations
- Retrievers or structured memory adapters

If your integration follows the LangChain Integration Contribution Guide, this will be recognised positively during judging.

We want this weekend to produce contributions that live beyond the event.

---

## Weekend schedule

### Friday - March 6

Kickoff & Team Formation

18:00 - Doors open (check-in, snacks, drinks)

19:00 - Opening remarks

19:30 - SurrealDB + LangChain recap demo

20:00 - Team formation (1-5 members) & hacking begins

### Saturday - March 7

Build Sprint + Mentor Support

10:00 - Doors open

**13:00 - Lunch**

14:00 - Mentor hours (technical support for APIs, integrations, architecture)

17:30 - Venue closes (teams may continue remotely)

### Sunday - March 8

Submission, Demos & Awards

10:00 - Final build push

12:00 - Strict submission deadline

**12:00 - Lunch**

12:45 - Video showcase of all projects

14:00 - Live demos + judging

15:30 - Winners announced

---

## Submission requirements

To be eligible for judging, each team must provide:

- A public GitHub repository
- A clear README (what it does + how to run it)
- A 2-minute project video overview (submission link will be shared per team)
- A live demo on Sunday

Projects that do not use both LangChain (or LangGraph) and SurrealDB will not be eligible for judging.

---

## Judging Criteria (100 Points)

Projects will be evaluated by engineers from SurrealDB and LangChain.

**30% - Structured Memory / Knowledge Usage (SurrealDB)**

Does the project use SurrealDB effectively for persistent context (graph, relational, or hybrid)? Does that context evolve during execution?

**20% - Agent Workflow Quality (LangChain / LangGraph)**

Is LangChain/LangGraph used clearly for orchestration, reasoning, and tool coordination?

**20% - Persistent Agent State**

Does the system handle multi-step state, checkpoints, or resumable flows?

**20% - Practical Use Case**

Does this solve a meaningful real-world problem?

**10% - Observability**

Can we follow the agent's execution (LangSmith trace preferred)?

### Bonus Consideration

Reusable LangChain integration contributions published as open-source.

---

## Prepare before you arrive (important)

- Ensure your Python or Node.js environment is ready
- Install Docker or the [**SurrealDB binary**](https://surrealdb.com/docs/surrealdb/installation) (if running SurrealDB locally), or create a [**free cloud account**](https://app.surrealdb.com/cloud)
- **Review:**
  - SurrealDB fundamentals
  - LangChain integrations
  - LangGraph state patterns
  - LangChain Integration Contribution Guide

Mentors will be available throughout the weekend to help with architecture decisions, debugging, and integrations.

---

## Helpful resources

- **How to Build a Knowledge Graph for AI:** https://surrealdb.com/blog/how-to-build-a-knowledge-graph-for-ai
- **LangChain Integration with SurrealDB:** https://surrealdb.com/docs/integrations/frameworks/langchain
- **SurrealDB Fundamentals:** https://surrealdb.com/learn/fundamentals
- **LangChain Integration Contribution Guide:** https://docs.langchain.com/oss/python/contributing/integrations-langchain

---

This weekend is about building agent systems that move beyond demos, toward structured, reliable, stateful applications.

See you in London.

Let's build something meaningful together.
