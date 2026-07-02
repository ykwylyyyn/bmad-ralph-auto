from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ralph.common.models import Story
from ralph.memory.skill_loader import SkillExcerpt
from ralph.pipeline.artifact.reader import (
    find_sprint_status,
    load_sprint_status,
    read_story_artifact,
    story_location_dir,
)


@dataclass(frozen=True, slots=True)
class PromptContext:
    project_dir: Path
    step: str = "dev"
    skill: SkillExcerpt | None = None
    story_body: str = ""
    atdd_checklist_path: str | None = None
    memory_events: list[dict[str, object]] = field(default_factory=list)
    max_chars: int = 32_000


_STEP_TITLES = {
    "atdd": "ATDD checklist and failing tests",
    "dev": "implementation",
    "qa": "QA review and test validation",
}


def build_story_prompt(story: Story) -> str:
    return build_step_prompt(story, "dev", PromptContext(project_dir=Path.cwd()))


def build_step_prompt(story: Story, step: str, context: PromptContext) -> str:
    title = _STEP_TITLES.get(step, step)
    lines = [
        f"Execute story cycle step `{step}` for story #{story.id}: {story.title}",
        f"Objective: {title}",
        "",
        "Story specification:",
    ]
    if story.key:
        lines.append(f"- Key: {story.key}")
    if story.acceptance_criteria:
        lines.append("")
        lines.append("Acceptance criteria:")
        lines.extend(f"- {criterion}" for criterion in story.acceptance_criteria)
    else:
        lines.append("- Complete the story according to project conventions.")

    if context.skill is not None:
        lines.extend(
            [
                "",
                "BMAD skill reference:",
                f"- Path: {context.skill.skill_path}",
                "",
                context.skill.excerpt,
            ]
        )

    if context.story_body.strip():
        lines.extend(["", "Story artifact:", context.story_body.strip()])

    if context.atdd_checklist_path:
        lines.extend(
            [
                "",
                "ATDD checklist:",
                f"- Path: {context.atdd_checklist_path}",
            ]
        )

    if context.memory_events:
        lines.append("")
        lines.append("Prior cycle events:")
        for event in context.memory_events[-5:]:
            lines.append(f"- {event}")

    lines.extend(
        [
            "",
            "Work only inside this repository worktree.",
            "Do not mark the story complete yourself; the pipeline will advance steps.",
        ]
    )

    prompt = "\n".join(lines)
    if len(prompt) > context.max_chars:
        prompt = prompt[: context.max_chars - 20].rstrip() + "\n\n[truncated]"
    return prompt


def load_prompt_context(
    project_dir: Path,
    story: Story,
    step: str,
    *,
    memory_events: list[dict[str, object]] | None = None,
    max_chars: int = 32_000,
) -> PromptContext:
    from ralph.memory.skill_loader import load_skill_excerpt

    skill = load_skill_excerpt(project_dir, step)
    story_body = _load_story_body(project_dir, story)
    atdd_path = _find_atdd_checklist(project_dir, story)
    return PromptContext(
        project_dir=project_dir,
        step=step,
        skill=skill,
        story_body=story_body,
        atdd_checklist_path=atdd_path,
        memory_events=memory_events or [],
        max_chars=max_chars,
    )


def _load_story_body(project_dir: Path, story: Story) -> str:
    if not story.key:
        return ""
    sprint_status_path = find_sprint_status(project_dir)
    if sprint_status_path is None:
        return ""
    try:
        sprint_status = load_sprint_status(sprint_status_path)
        story_dir = story_location_dir(sprint_status, sprint_status_path)
        artifact = read_story_artifact(story_dir, story.key)
    except Exception:
        return ""
    return artifact.body.strip()


def _find_atdd_checklist(project_dir: Path, story: Story) -> str | None:
    if not story.key:
        return None
    candidates = [
        project_dir / "_bmad-output" / "test-artifacts" / f"atdd-checklist-{story.key}.md",
        project_dir / "_bmad-output" / "test-artifacts" / f"story-{story.key}-atdd.md",
    ]
    for path in candidates:
        if path.is_file():
            return str(path.relative_to(project_dir.resolve()))
    return None
