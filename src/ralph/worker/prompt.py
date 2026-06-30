from __future__ import annotations

from ralph.common.models import Story


def build_story_prompt(story: Story) -> str:
    lines = [
        f"Implement story #{story.id}: {story.title}",
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
    lines.append("")
    lines.append("Work only inside this repository worktree and satisfy every acceptance criterion.")
    return "\n".join(lines)
