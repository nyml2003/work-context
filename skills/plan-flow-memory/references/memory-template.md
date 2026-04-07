# Memory Template

Use this structure when creating or updating `plan-flow-memory.md`.

## File header

```md
# Plan Flow Memory

This file stores user-approved workflow optimizations for recurring planning and process issues.
Update entries only after explicit user approval.

## Entries
```

## Entry shape

```md
### Repeated Scope Clarification
<!-- plan-flow-memory:key=repeated-scope-clarification -->
- Pattern: Plans keep stalling because scope boundaries are not explicit at the start.
- Trigger Signals:
  - Repeated scope questions appear before work decomposition stabilizes.
  - The plan changes after hidden non-goals surface.
- Recommended Workflow:
  1. Restate the goal, non-goals, and constraints before detailed planning.
  2. Ask only the minimum blocking scope questions.
  3. Freeze scope before task decomposition.
- Scope: Planning, scoping, and execution-prep conversations.
- Skip When:
  - The task is trivial.
  - The user explicitly wants immediate execution without a plan.
- Source Note: Confirmed after repeated scope clarification during planning.
- Updated: 2026-04-06T12:00:00+00:00
```

## Key rules

- Use stable ASCII keys such as `repeated-scope-clarification`.
- Generalize the lesson so it applies to future tasks.
- Prefer three to five workflow steps.
- Update existing entries instead of appending duplicates.
