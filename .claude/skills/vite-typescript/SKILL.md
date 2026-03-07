---
name: vite-typescript
description: Build and maintain Vite + TypeScript frontends with reliable state, API integration, accessibility, and performance-focused UI architecture. Use for React TS app structure, build/debug, and UX delivery.
---

# Vite TypeScript Skill

Use this skill for frontend work in Vite + React + TypeScript projects.

## When to apply

- Adding new React UI features in TypeScript
- Refactoring component/state architecture
- Integrating frontend API calls and error states
- Improving accessibility, responsiveness, and performance
- Debugging Vite build/dev issues

## Workflow

1. Map user journey first.
- Identify entry interaction, loading states, success states, and failure states.
- Define the exact API contracts used by the UI.

2. Type every boundary.
- Create explicit TypeScript types for API payloads.
- Normalize server values before rendering.

3. Keep UI state intentional.
- Separate server data, UI state, and derived view models.
- Avoid mixing fetch side effects and rendering logic.

4. Build resilient data fetching.
- Handle pending/empty/error/success for each async surface.
- Keep stale data behavior explicit during refetch.

5. Preserve UX quality.
- Maintain keyboard interactions and focus visibility.
- Ensure mobile and desktop layouts both work.
- Add visual hierarchy with clear, purposeful sectioning.

6. Validate runtime.
- Run build/lint after changes.
- Check for TypeScript narrowing and null-safety regressions.

## Patterns to prefer

- Small, typed presentational components
- Composable hooks/utilities for repeated view logic
- Explicit loading/error components for each panel
- Stable keys and memoization only when necessary

## Anti-patterns

- `any` at API boundaries
- Silent fetch failures with no UI feedback
- One giant component owning unrelated concerns
- Styling and state logic tightly coupled in unreadable blocks

## Validation checklist

- `npm run build` passes
- New UI flows have loading/empty/error handling
- Keyboard submit and focus behavior still works
- All new API responses are typed and normalized
