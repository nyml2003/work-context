---
name: "codex-skill-authoring"
description: "Use this skill when creating or maintaining Codex skills, including SKILL.md frontmatter, agents/openai.yaml metadata, and bundled references or scripts."
metadata:
  short-description: "Maintain Codex skills"
---

# Codex Skill Authoring

## Overview

This skill helps maintain Codex-native skills that live as folders containing `SKILL.md` plus optional `agents/`, `references/`, `scripts/`, and `assets/` resources.

## Workflow

1. Start from the current repository structure rather than inventing new metadata files.
2. Keep `SKILL.md` concise and move deep details into `references/`.
3. Ensure `agents/openai.yaml` stays consistent with the skill purpose and invocation name.
4. Prefer deterministic scripts for repetitive or fragile operations.

