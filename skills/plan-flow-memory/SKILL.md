---
name: "plan-flow-memory"
description: "Use when Codex should detect reusable planning or workflow problems during any task, summarize what can be learned, ask whether the user wants to optimize the process, and persist confirmed workflow rules into memory. Trigger on planning, task decomposition, scoping, execution prep, retrospective, repeated clarification, process friction, workflow optimization, 计划, 复盘, 流程优化, 记住这种做法, 下次别再重复问, or similar requests to turn recurring process issues into reusable rules."
metadata:
  short-description: "Capture plan issues and workflow memory"
  workbench:
    role-fit:
      - "policy"
    domain-tags:
      - "planning"
      - "workflow"
      - "memory"
    capabilities:
      - "plan-flow-optimization"
      - "workflow-memory"
    default-blocks:
      - "overview"
      - "plan-issue-taxonomy"
      - "memory-template"
      - "record-memory"
    recommends: []
    handoff-outputs:
      - "plan-flow-memory-summary"
    blocks:
      - name: "overview"
        kind: "overview"
      - name: "plan-issue-taxonomy"
        kind: "reference"
        path: "references/plan-issue-taxonomy.md"
      - name: "memory-template"
        kind: "reference"
        path: "references/memory-template.md"
      - name: "record-memory"
        kind: "script_entry"
        path: "scripts/upsert_memory.py"
---

# Plan Flow Memory

## Default Stance

- Treat repeated planning friction as a reusable workflow signal, not just a local annoyance.
- Ask whether to optimize the process every time a clear plan-worthy issue appears.
- Persist memory only after explicit user approval.
- Match the user's language when summarizing the issue and asking for confirmation.

## Workflow

1. Detect a plan-worthy issue. Use `references/plan-issue-taxonomy.md` to classify it before asking anything.
2. Summarize the issue in one or two sentences: what repeated, why it slowed the task, and what a better workflow would change.
3. Ask a direct confirmation question. Default shape: "I see a repeatable planning issue here: <summary>. Do you want me to turn it into a reusable workflow rule and remember it for next time?" Use the user's language.
4. If the user says yes, derive a stable ASCII pattern key, generalize the lesson, shape the entry with `references/memory-template.md`, and write it with `scripts/upsert_memory.py`.
5. On future similar tasks, read the memory file first and apply the stored workflow before repeating the same clarification loop.

## Detection Rules

1. Broad trigger: scan any task for planning, scoping, decomposition, execution prep, retrospective, or repeated process friction.
2. A plan-worthy issue must be reusable beyond the exact task. Prefer patterns such as missing success criteria, repeated scope clarification, unstable assumptions, repeated handoff gaps, or recurring review/test omissions.
3. Do not record one-off project facts, temporary preferences, or raw conversation transcripts.
4. If the user declines optimization, acknowledge it and do not write memory.
5. If multiple symptoms point to one underlying issue, ask once and record one generalized rule.

## Memory Rules

1. Default memory file: `C:\Users\DELL\.codex\memories\plan-flow-memory.md`.
2. Store durable rules with: pattern, trigger signals, recommended workflow, scope, skip conditions, source note, and updated timestamp.
3. Update an existing entry when the same pattern key appears. Do not append duplicates.
4. Keep each entry human-readable Markdown. Optimize for reuse, not exhaustiveness.

## Output Requirements

- Issue summary
- Confirmation question
- Generalized workflow rule if approved
- Memory write result, or an explicit note that no memory was written
