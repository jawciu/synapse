---
name: surrealdb
description: Design and query SurrealDB for graph and hybrid vector use cases. Use for schema design, edge modeling, indexing, query optimization, migration-safe updates, and graph+vector retrieval patterns.
---

# SurrealDB Skill

Use this skill when changing SurrealDB schema, graph logic, or semantic retrieval.

## When to apply

- Modeling entity and relation tables
- Adding or changing SurrealQL queries
- Implementing graph traversals for agent tools
- Adding vector similarity behavior and indexes
- Hardening user partitioning and query safety

## Workflow

1. Model from use case.
- Start with user questions the graph must answer.
- Define node tables, relation tables, and required fields.

2. Make tenancy explicit.
- Ensure every table/query is scoped by `user_id` where required.
- Verify no cross-user reads in traversal queries.

3. Separate node and edge semantics.
- Store canonical facts on nodes.
- Store contextual links and counts on relation tables.

4. Add retrieval paths.
- Structured path: edge traversal queries for exact relationships.
- Semantic path: vector similarity for fuzzy language.
- Hybrid path: merge both for final context selection.

5. Index intentionally.
- Add vector indexes only on tables used for semantic lookup.
- Keep distance metric and KNN syntax consistent across queries.

6. Validate with realistic data.
- Test queries against seeded long-tail examples.
- Validate empty-state behavior and malformed data handling.

## Patterns to prefer

- Typed graph tables with minimal but sufficient fields
- Relation tables for event or link semantics
- Stable IDs and timestamps for temporal queries
- Short, composable queries for tool wrappers

## Anti-patterns

- Storing relationship meaning as denormalized text only
- Running semantic search without user scoping
- Overloading one table with unrelated entity shapes
- Hidden query assumptions about missing fields

## Validation checklist

- Schema init is idempotent
- Queries are user-scoped and null-safe
- Graph traversal results align with expected edge semantics
- Vector queries return stable top-k results with clear ordering
