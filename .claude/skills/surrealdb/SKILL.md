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

## Surrealist-first querying rules (important)

1. Prefer traversal queries that return full records.
- Use `->edge->table.*` paths from a root table (`reflection`, `person`, `pattern`).
- Add `FETCH` for relation names so graph view has concrete linked records.

2. SurrealQL ordering rule.
- When using `ORDER BY field`, include that `field` in `SELECT`.
- If you get `Missing order idiom ... in statement selection`, add the ordered field to the projection.

3. Understand disconnected graph clusters.
- In Surrealist graph view, separate blobs usually mean disconnected subgraphs, not "one blob per person."
- Common cause in this repo: mixed `user_id` cohorts or non-overlapping reflection links.

4. Be explicit about user partitioning in demos.
- App-written rows use `user_id` values like `app_user:<id>`.
- Seeded rows from `seed_data.py` are typically `user_id = NONE`.
- Provide all three query modes when sharing examples: all rows, one `$uid`, and `user_id = NONE`.

## Known-good query templates for this repo

### Find available cohorts

```sql
SELECT user_id, count() AS reflections
FROM reflection
GROUP BY user_id
ORDER BY reflections DESC;
```

### Reflection-centered graph (all users)

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
LIMIT 8
FETCH reveals, activates, triggers_schema, expresses, about, mentions;
```

### Reflection graph scoped to one user

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

### Reflection graph scoped to seeded data

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

### Edge-only graph view

```sql
SELECT * FROM reveals LIMIT 120 FETCH in, out;
SELECT * FROM co_occurs_with LIMIT 120 FETCH in, out;
SELECT * FROM triggers_pattern LIMIT 120 FETCH in, out;
SELECT * FROM mentions LIMIT 120 FETCH in, out;
```

## Demo troubleshooting loop

1. Check data exists.
- `SELECT count() AS total FROM reflection GROUP ALL;`

2. Check partitions.
- `SELECT user_id, count() AS reflections FROM reflection GROUP BY user_id;`

3. If graph looks fragmented, run one-user query.
- Filter by `WHERE user_id = $uid` (or `WHERE user_id = NONE` for seeded data).

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
