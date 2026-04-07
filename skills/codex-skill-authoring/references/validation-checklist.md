# Validation Checklist

- `SKILL.md` starts with valid YAML front matter.
- `name` uses lowercase hyphen-case and matches the folder name.
- `description` clearly states what the skill does and when to use it.
- For top-level skills, `agents/openai.yaml` uses quoted strings and its `default_prompt` mentions `$skill-name`.
- For internal modules under `references/**/<name>/`, `agents/openai.yaml` is optional; if kept, treat it as preserved module metadata rather than a discovery requirement.
- Internal modules still need a real `SKILL.md`, a matching folder name, and any referenced `references/`, `scripts/`, or `assets/` paths must exist.
