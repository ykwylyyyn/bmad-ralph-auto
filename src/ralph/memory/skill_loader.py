from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

STEP_SKILL_PREFIXES: dict[str, tuple[str, ...]] = {
    "atdd": ("bmad-tea-atdd", "bmad-atdd"),
    "dev": ("bmad-bmm-dev-story", "bmad-dev-story"),
    "qa": ("bmad-bmm-qa", "bmad-qa", "bmad-bmm-qa-story"),
}

DEFAULT_SKILL_MAX_LINES = 40


@dataclass(frozen=True, slots=True)
class SkillExcerpt:
    step: str
    skill_path: str
    excerpt: str


def find_skill_dir(project_dir: Path, step: str) -> Path | None:
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.is_dir():
        return None

    prefixes = STEP_SKILL_PREFIXES.get(step, ())
    for path in sorted(skills_dir.iterdir()):
        if not path.is_dir():
            continue
        name = path.name.lower()
        if any(name.startswith(prefix) for prefix in prefixes):
            return path
    return None


def load_skill_excerpt(
    project_dir: Path,
    step: str,
    *,
    max_lines: int = DEFAULT_SKILL_MAX_LINES,
) -> SkillExcerpt | None:
    skill_dir = find_skill_dir(project_dir, step)
    if skill_dir is None:
        return None

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None

    try:
        lines = skill_md.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    excerpt = "\n".join(lines[:max_lines]).strip()
    if not excerpt:
        return None

    return SkillExcerpt(
        step=step,
        skill_path=str(skill_md.relative_to(project_dir.resolve())),
        excerpt=excerpt,
    )


def load_customize_workflow(skill_dir: Path) -> str | None:
    customize = skill_dir / "customize.toml"
    if not customize.is_file():
        return None
    try:
        import tomllib

        data = tomllib.loads(customize.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    workflow = data.get("workflow")
    if isinstance(workflow, str) and workflow.strip():
        return workflow.strip()
    return None
