from __future__ import annotations

from pathlib import Path

from ralph.render.components import (
    completion_summary,
    health_line,
    progress_bar,
    section_border,
    summary_line,
)
from ralph.render.theme import Semantic, Theme
from ralph.render.timefmt import format_duration_between

from .snapshot import StatusSnapshot, should_show_status_hint
from .tables import (
    hint_line,
    story_detail_sections,
    story_table,
    worker_detail_sections,
    worker_table,
)


def render_status_overview(snapshot: StatusSnapshot, *, theme: Theme) -> str:
    lines: list[str] = []
    lines.append(
        section_border(
            "Ralph",
            context=snapshot.health_label,
            context_semantic=_health_semantic(snapshot.health_label),
            theme=theme,
        )
    )
    lines.append(_render_health_line(snapshot, theme=theme))

    if snapshot.total_stories > 0:
        lines.extend(
            progress_bar(
                snapshot.story_counts.completed,
                snapshot.total_stories,
                theme=theme,
            )
        )
        lines.append(summary_line(snapshot.story_counts.as_dict(), theme=theme))

    if snapshot.is_complete:
        lines.extend(
            completion_summary(
                success_percent=snapshot.success_percent,
                self_healed=snapshot.self_healed_count,
                failed=snapshot.story_counts.failed,
                runtime=format_duration_between(snapshot.started_at, snapshot.heartbeat_at),
                worker_count=max(snapshot.active_workers, snapshot.max_workers),
                failed_stories=snapshot.failed_story_ids,
                theme=theme,
            )
        )

    return "\n".join(lines)


def render_status_tables(snapshot: StatusSnapshot, *, theme: Theme) -> str:
    lines: list[str] = []
    if snapshot.stories:
        lines.extend(story_table(snapshot.stories, theme=theme))
    if snapshot.workers:
        if lines:
            lines.append("")
        lines.extend(
            worker_table(
                snapshot.workers,
                theme=theme,
                healthy_count=snapshot.healthy_worker_count,
            )
        )
    return "\n".join(lines)


def render_status_detail(snapshot: StatusSnapshot, *, theme: Theme) -> str:
    lines: list[str] = []
    story_sections = story_detail_sections(snapshot.stories, theme=theme)
    worker_sections = worker_detail_sections(snapshot.workers, theme=theme)
    if story_sections:
        lines.extend(story_sections)
    if worker_sections:
        if lines:
            lines.append("")
        lines.extend(worker_sections)
    return "\n".join(lines)


def render_status(
    snapshot: StatusSnapshot,
    *,
    theme: Theme,
    project_dir: str | Path,
    detail: bool = False,
) -> str:
    sections = [render_status_overview(snapshot, theme=theme)]
    tables = render_status_tables(snapshot, theme=theme)
    if tables:
        sections.append(tables)
    if detail:
        detail_output = render_status_detail(snapshot, theme=theme)
        if detail_output:
            sections.append(detail_output)
    if should_show_status_hint(project_dir) and not detail:
        sections.append(hint_line("ralph status --detail for expanded view", theme=theme))
    return "\n\n".join(section for section in sections if section)


def _health_semantic(label: str) -> Semantic:
    if label == "healthy":
        return Semantic.HEALTHY
    if label == "complete":
        return Semantic.HEALTHY
    if label == "healing":
        return Semantic.ACTIVE
    if label == "error":
        return Semantic.FAILED
    return Semantic.DEFAULT


def _render_health_line(snapshot: StatusSnapshot, *, theme: Theme) -> str:
    runtime = format_duration_between(snapshot.started_at, snapshot.heartbeat_at)
    worker_count = snapshot.active_workers or snapshot.max_workers

    if snapshot.health_label == "complete":
        text = f"Sprint finished in {runtime} with {worker_count} workers"
        return health_line(text, theme=theme, semantic=Semantic.HEALTHY)
    if snapshot.health_label == "healing":
        recovery = snapshot.recovery_story_count
        noun = "story" if recovery == 1 else "stories"
        text = f"Running for {runtime} — {recovery} {noun} in recovery"
        return health_line(text, theme=theme, semantic=Semantic.ACTIVE)
    if snapshot.health_label == "error":
        return health_line(
            "Daemon error — see ralph diagnose for details",
            theme=theme,
            semantic=Semantic.FAILED,
        )
    if snapshot.total_stories == 0:
        return health_line(
            f"Running for {runtime} — no stories loaded",
            theme=theme,
        )
    return health_line(
        f"Running for {runtime} with {worker_count} workers",
        theme=theme,
    )
