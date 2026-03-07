---
name: python
description: Build maintainable Python backend and service code with strong typing, safe error handling, clean module boundaries, and testable workflows. Use for FastAPI services, data pipelines, and integration-heavy Python changes.
---

# Python Skill

Use this skill for Python backend, service, and pipeline work.

## When to apply

- FastAPI endpoint design and request/response contracts
- Service-layer refactors and orchestration logic
- Error handling and reliability hardening
- Data processing and integration workflows
- Type-driven cleanup and maintainability improvements

## Workflow

1. Start from contracts.
- Define input/output schemas first.
- Keep transport models separate from business logic.

2. Keep modules focused.
- API routes: auth + validation + response mapping.
- Service layer: orchestration and domain rules.
- Data layer: storage/query concerns only.

3. Make failure modes explicit.
- Convert exceptions into actionable error responses.
- Add fallback behavior for external/model failures where needed.

4. Type and document critical paths.
- Add precise type hints on function boundaries.
- Keep complex behavior in small named functions.

5. Keep side effects controlled.
- Centralize environment/config access.
- Avoid hidden globals unless lifecycle is explicit.

6. Validate before ship.
- Run target tests/build checks.
- Confirm no regressions in endpoint contracts.

## Patterns to prefer

- Pydantic models for API boundaries
- Service wrappers for orchestration flows
- Idempotent startup/init routines
- Structured logging around integration boundaries

## Anti-patterns

- Endpoint handlers with embedded business logic
- Catch-all exceptions that hide root causes
- Implicit type conversions at runtime boundaries
- Global mutable state without init discipline

## Validation checklist

- Endpoint contracts match actual responses
- Error paths return stable HTTP semantics
- State/init code is deterministic on restart
- Core functions are typed and reviewable
