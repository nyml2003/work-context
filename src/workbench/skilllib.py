from __future__ import annotations

import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .config import WorkbenchConfig
from .fs import read_json, render_template, short_path, slugify, write_text
from .yamlish import YamlError, dumps as yaml_dumps, loads as yaml_loads

ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESOURCE_PATTERN = re.compile(r"(?P<path>(?:agents|references|scripts|assets)/[A-Za-z0-9._/\-]+)")
RESOURCE_CHOICES = ("scripts", "references", "assets")


@dataclass
class Skill:
    name: str
    description: str
    body: str
    frontmatter: dict[str, Any]
    path: Path
    agents_path: Path | None
    agents_config: dict[str, Any] | None
    references: list[Path]
    scripts: list[Path]
    assets: list[Path]
    examples: list[Path]
    tests: list[Path]

    def to_record(self, root: Path) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("body", None)
        payload["path"] = short_path(self.path, root)
        payload["agents_path"] = short_path(self.agents_path, root) if self.agents_path else None
        payload["references"] = [short_path(path, root) for path in self.references]
        payload["scripts"] = [short_path(path, root) for path in self.scripts]
        payload["assets"] = [short_path(path, root) for path in self.assets]
        payload["examples"] = [short_path(path, root) for path in self.examples]
        payload["tests"] = [short_path(path, root) for path in self.tests]
        return payload


def _title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def _split_frontmatter(content: str, path: Path) -> tuple[dict[str, Any], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} is missing YAML front matter")
    try:
        end_index = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError(f"{path} has unterminated YAML front matter") from exc
    metadata_text = "\n".join(lines[1:end_index])
    metadata = yaml_loads(metadata_text)
    if not isinstance(metadata, dict):
        raise ValueError(f"{path} front matter must be a mapping")
    body = "\n".join(lines[end_index + 1 :]).strip() + "\n"
    return metadata, body


def _load_markdown_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    return _split_frontmatter(path.read_text(encoding="utf-8"), path)


def _load_openai_yaml(path: Path) -> dict[str, Any]:
    raw = yaml_loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def discover_skill_dirs(config: WorkbenchConfig) -> list[Path]:
    if not config.skills_dir.exists():
        return []
    return sorted(skill_md.parent for skill_md in config.skills_dir.rglob("SKILL.md"))


def load_skill(skill_dir: Path) -> Skill:
    frontmatter, body = _load_markdown_frontmatter(skill_dir / "SKILL.md")
    if "name" not in frontmatter:
        raise ValueError(f"{skill_dir / 'SKILL.md'} is missing front matter key 'name'")
    if "description" not in frontmatter:
        raise ValueError(f"{skill_dir / 'SKILL.md'} is missing front matter key 'description'")
    if not isinstance(frontmatter["name"], str):
        raise ValueError(f"{skill_dir / 'SKILL.md'} front matter key 'name' must be a string")
    if not isinstance(frontmatter["description"], str):
        raise ValueError(f"{skill_dir / 'SKILL.md'} front matter key 'description' must be a string")
    agents_path = skill_dir / "agents" / "openai.yaml"
    agents_config = _load_openai_yaml(agents_path) if agents_path.exists() else None
    return Skill(
        name=frontmatter["name"],
        description=frontmatter["description"],
        body=body,
        frontmatter=frontmatter,
        path=skill_dir,
        agents_path=agents_path if agents_path.exists() else None,
        agents_config=agents_config,
        references=sorted(path for path in (skill_dir / "references").rglob("*") if path.is_file()) if (skill_dir / "references").exists() else [],
        scripts=sorted(path for path in (skill_dir / "scripts").rglob("*") if path.is_file()) if (skill_dir / "scripts").exists() else [],
        assets=sorted(path for path in (skill_dir / "assets").rglob("*") if path.is_file()) if (skill_dir / "assets").exists() else [],
        examples=sorted((skill_dir / "examples").glob("*.json")) if (skill_dir / "examples").exists() else [],
        tests=sorted((skill_dir / "tests").glob("*.json")) if (skill_dir / "tests").exists() else [],
    )


def discover_skills(config: WorkbenchConfig) -> list[Skill]:
    return [load_skill(skill_dir) for skill_dir in discover_skill_dirs(config)]


def _skill_templates(config: WorkbenchConfig) -> tuple[str, str, str, str, str]:
    skill_template_path = config.templates_dir / "skill" / "SKILL.md.tpl"
    openai_template_path = config.templates_dir / "skill" / "openai.yaml.tpl"
    reference_template_path = config.templates_dir / "skill" / "reference.md.tpl"
    script_template_path = config.templates_dir / "skill" / "script.py.tpl"
    asset_template_path = config.templates_dir / "skill" / "asset.txt.tpl"
    return (
        skill_template_path.read_text(encoding="utf-8"),
        openai_template_path.read_text(encoding="utf-8"),
        reference_template_path.read_text(encoding="utf-8"),
        script_template_path.read_text(encoding="utf-8"),
        asset_template_path.read_text(encoding="utf-8"),
    )


def create_skill(
    config: WorkbenchConfig,
    name: str,
    *,
    description: str,
    resources: list[str] | None = None,
    include_examples: bool = False,
    short_description: str | None = None,
    default_prompt: str | None = None,
) -> Path:
    skill_name = slugify(name)
    skill_dir = config.skills_dir / skill_name
    if skill_dir.exists():
        raise FileExistsError(f"Skill already exists: {skill_dir}")
    selected_resources = list(dict.fromkeys(resources or []))
    for resource in selected_resources:
        if resource not in RESOURCE_CHOICES:
            raise ValueError(f"Unknown resource type: {resource}")
    title = _title_from_name(skill_name)
    short = short_description or title
    prompt = default_prompt or f"Use ${skill_name} to handle this task."
    skill_tpl, openai_tpl, reference_tpl, script_tpl, asset_tpl = _skill_templates(config)
    context = {
        "name": skill_name,
        "title": title,
        "description": description,
        "short_description": short,
        "default_prompt": prompt,
        "overview": "Describe what this skill enables and what it should avoid.",
    }
    write_text(skill_dir / "SKILL.md", render_template(skill_tpl, context))
    openai_content = render_template(openai_tpl, context)
    openai_payload = yaml_loads(openai_content)
    write_text(skill_dir / "agents" / "openai.yaml", yaml_dumps(openai_payload))
    write_text(skill_dir / "examples" / "basic.json", '{\n  "request": "Replace with a realistic user request."\n}\n')
    write_text(
        skill_dir / "tests" / "basic.json",
        '{\n  "bundle_contains": ["%s"],\n  "reference_count": %d\n}\n'
        % (skill_name, 1 if include_examples and "references" in selected_resources else 0),
    )
    for resource in selected_resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir(parents=True, exist_ok=True)
        if not include_examples:
            continue
        if resource == "references":
            write_text(resource_dir / "overview.md", render_template(reference_tpl, {"title": title}))
        elif resource == "scripts":
            write_text(resource_dir / "example.py", render_template(script_tpl, {"name": skill_name}))
        elif resource == "assets":
            write_text(resource_dir / "README.txt", asset_tpl)
    return skill_dir


def _validate_frontmatter(skill: Skill, issues: list[dict[str, str]], root: Path) -> None:
    unexpected = sorted(set(skill.frontmatter) - ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        issues.append(
            {
                "level": "error",
                "message": f"Unexpected front matter keys: {', '.join(unexpected)}",
                "path": short_path(skill.path / 'SKILL.md', root),
            }
        )
    if not NAME_PATTERN.fullmatch(skill.name):
        issues.append(
            {
                "level": "error",
                "message": f"Invalid skill name '{skill.name}'. Use lowercase hyphen-case.",
                "path": short_path(skill.path / "SKILL.md", root),
            }
        )
    if skill.path.name != skill.name:
        issues.append(
            {
                "level": "error",
                "message": f"Directory name '{skill.path.name}' does not match skill name '{skill.name}'",
                "path": short_path(skill.path, root),
            }
        )
    description = skill.description.strip()
    if not description:
        issues.append({"level": "error", "message": "Description cannot be empty", "path": short_path(skill.path / "SKILL.md", root)})
    if "<" in description or ">" in description:
        issues.append({"level": "error", "message": "Description cannot contain angle brackets", "path": short_path(skill.path / "SKILL.md", root)})
    if len(description) > 1024:
        issues.append({"level": "error", "message": "Description is too long", "path": short_path(skill.path / "SKILL.md", root)})


def _validate_agents(skill: Skill, issues: list[dict[str, str]], root: Path) -> None:
    if skill.agents_path is None:
        return
    data = skill.agents_config or {}
    interface = data.get("interface", {})
    if not isinstance(interface, dict):
        issues.append({"level": "error", "message": "agents/openai.yaml interface must be a mapping", "path": short_path(skill.agents_path, root)})
        return
    short_description = interface.get("short_description")
    if short_description is not None and not isinstance(short_description, str):
        issues.append({"level": "error", "message": "interface.short_description must be a string", "path": short_path(skill.agents_path, root)})
    default_prompt = interface.get("default_prompt")
    if default_prompt is not None:
        if not isinstance(default_prompt, str):
            issues.append({"level": "error", "message": "interface.default_prompt must be a string", "path": short_path(skill.agents_path, root)})
        elif f"${skill.name}" not in default_prompt:
            issues.append({"level": "warning", "message": f"interface.default_prompt should mention ${skill.name}", "path": short_path(skill.agents_path, root)})
    policy = data.get("policy", {})
    if policy and not isinstance(policy, dict):
        issues.append({"level": "error", "message": "policy must be a mapping", "path": short_path(skill.agents_path, root)})
    allow_implicit = policy.get("allow_implicit_invocation")
    if allow_implicit is not None and not isinstance(allow_implicit, bool):
        issues.append({"level": "error", "message": "policy.allow_implicit_invocation must be boolean", "path": short_path(skill.agents_path, root)})


def _validate_resource_mentions(skill: Skill, issues: list[dict[str, str]], root: Path) -> None:
    for match in RESOURCE_PATTERN.finditer(skill.body):
        candidate = skill.path / Path(match.group("path"))
        if not candidate.exists():
            issues.append(
                {
                    "level": "error",
                    "message": f"Referenced resource does not exist: {match.group('path')}",
                    "path": short_path(skill.path / "SKILL.md", root),
                }
            )


def _validate_examples_and_tests(skill: Skill, issues: list[dict[str, str]], root: Path) -> None:
    for example_path in skill.examples:
        try:
            read_json(example_path)
        except Exception as exc:  # pragma: no cover
            issues.append({"level": "error", "message": f"Invalid example JSON: {exc}", "path": short_path(example_path, root)})
    for test_path in skill.tests:
        try:
            fixture = read_json(test_path)
        except Exception as exc:  # pragma: no cover
            issues.append({"level": "error", "message": f"Invalid test JSON: {exc}", "path": short_path(test_path, root)})
            continue
        if "bundle_contains" not in fixture:
            issues.append({"level": "error", "message": "Test fixture missing bundle_contains", "path": short_path(test_path, root)})


def lint_skills(config: WorkbenchConfig, skill_name: str | None = None) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    skills: list[Skill] = []
    selected_dirs = discover_skill_dirs(config)
    if skill_name is not None:
        selected_dirs = [item for item in selected_dirs if item.name == skill_name]
        if not selected_dirs:
            issues.append({"level": "error", "message": f"Skill '{skill_name}' not found", "path": short_path(config.skills_dir, config.root)})
    for skill_dir in selected_dirs:
        try:
            skill = load_skill(skill_dir)
        except (OSError, ValueError, YamlError) as exc:
            issues.append({"level": "error", "message": str(exc), "path": short_path(skill_dir, config.root)})
            continue
        skills.append(skill)
        _validate_frontmatter(skill, issues, config.root)
        _validate_agents(skill, issues, config.root)
        _validate_resource_mentions(skill, issues, config.root)
        _validate_examples_and_tests(skill, issues, config.root)
    return {
        "skill_count": len(skills),
        "issue_count": len(issues),
        "skills": [skill.to_record(config.root) for skill in skills],
        "issues": issues,
    }


def render_bundle(skill: Skill, config: WorkbenchConfig) -> tuple[str, list[dict[str, str]]]:
    references = [path for path in skill.references if path.is_file()]
    sections = [
        "# Skill Bundle",
        "",
        f"- name: {skill.name}",
        f"- path: {short_path(skill.path, config.root)}",
        "",
        "## SKILL.md Front Matter",
        "",
        yaml_dumps(skill.frontmatter).strip(),
        "",
        "## SKILL.md Body",
        "",
        skill.body.strip(),
        "",
    ]
    if skill.agents_path and skill.agents_config:
        sections.extend(
            [
                "## agents/openai.yaml",
                "",
                yaml_dumps(skill.agents_config).strip(),
                "",
            ]
        )
    linked_refs: list[dict[str, str]] = []
    if references:
        sections.extend(["## references/", ""])
        for ref_path in references:
            linked_refs.append({"path": short_path(ref_path, config.root), "name": ref_path.name})
            sections.extend(
                [
                    f"### {ref_path.name}",
                    "",
                    ref_path.read_text(encoding="utf-8").strip(),
                    "",
                ]
            )
    return "\n".join(sections).rstrip() + "\n", linked_refs


def test_skills(config: WorkbenchConfig, skill_name: str | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    failures = 0
    for skill in discover_skills(config):
        if skill_name is not None and skill.name != skill_name:
            continue
        bundle, references = render_bundle(skill, config)
        if not skill.tests:
            results.append({"skill": skill.name, "status": "skipped", "reason": "No test fixtures"})
            continue
        for fixture_path in skill.tests:
            fixture = read_json(fixture_path)
            missing_strings = [token for token in fixture.get("bundle_contains", []) if token not in bundle]
            expected_count = fixture.get("reference_count")
            count_ok = expected_count is None or expected_count == len(references)
            passed = not missing_strings and count_ok
            if not passed:
                failures += 1
            results.append(
                {
                    "skill": skill.name,
                    "fixture": short_path(fixture_path, config.root),
                    "status": "passed" if passed else "failed",
                    "missing_strings": missing_strings,
                    "expected_reference_count": expected_count,
                    "actual_reference_count": len(references),
                }
            )
    return {"failure_count": failures, "results": results}


def pack_skill(config: WorkbenchConfig, skill_name: str, *, output_path: Path | None = None) -> Path:
    skill = next((item for item in discover_skills(config) if item.name == skill_name), None)
    if skill is None:
        raise FileNotFoundError(f"Skill not found: {skill_name}")
    if output_path is None:
        output_path = config.reports_dir / f"{skill.name}.zip"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in skill.path.rglob("*") if path.is_file()):
            archive.write(file_path, arcname=file_path.relative_to(config.root))
    return output_path


def sync_skills(
    config: WorkbenchConfig,
    *,
    skill_name: str | None = None,
    target_root: Path | None = None,
    overwrite: bool = True,
) -> list[dict[str, str]]:
    target = target_root or config.codex_install_root
    target.mkdir(parents=True, exist_ok=True)
    synced: list[dict[str, str]] = []
    for skill in discover_skills(config):
        if skill_name is not None and skill.name != skill_name:
            continue
        destination = target / skill.name
        if destination.exists():
            if not overwrite:
                raise FileExistsError(f"Destination already exists: {destination}")
            shutil.rmtree(destination)
        shutil.copytree(skill.path, destination)
        synced.append({"skill": skill.name, "destination": str(destination)})
    if skill_name is not None and not synced:
        raise FileNotFoundError(f"Skill not found: {skill_name}")
    return synced
