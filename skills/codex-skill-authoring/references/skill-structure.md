# Skill Structure

Every top-level Codex skill must include a `SKILL.md` file with YAML front matter containing at least `name` and `description`.

Top-level entrypoint shape:

- `skills/<name>/SKILL.md`
- Optional `agents/`, `references/`, `scripts/`, `assets/`, `tests/`, `examples/`

Internal skill-shaped module shape:

- `<parent>/references/**/<name>/SKILL.md`
- Keeps the same `SKILL.md` format for staged loading and validation
- May keep its own `references/`, `scripts/`, `assets/`, `tests/`, `examples/`, and even `agents/`
- Is not independently discovered or linked as a top-level skill

Optional directories:

- `agents/` for UI-facing metadata
- `references/` for load-on-demand documentation
- `scripts/` for deterministic helper code
- `assets/` for files used in outputs
