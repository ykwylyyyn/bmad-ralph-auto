from __future__ import annotations

from ralph.render.components import section_border
from ralph.render.theme import Semantic, Theme
from ralph.render.width import story_name_limit, truncate_text

from .snapshot import StoryDetail, WorkerDetail

_STORY_COLUMNS = {
    "id": 4,
    "name": 20,
    "state": 11,
    "worker": 6,
    "duration": 9,
    "retries": 7,
}

_STATE_SEMANTICS = {
    "completed": Semantic.HEALTHY,
    "running": Semantic.ACTIVE,
    "retrying": Semantic.ACTIVE,
    "restarting": Semantic.ACTIVE,
    "diagnosing": Semantic.ACTIVE,
    "queued": Semantic.SECONDARY,
    "blocked": Semantic.SECONDARY,
    "failed": Semantic.FAILED,
}

_HEALTH_SEMANTICS = {
    "healthy": Semantic.HEALTHY,
    "idle": Semantic.SECONDARY,
    "restarting": Semantic.ACTIVE,
    "degraded": Semantic.ACTIVE,
    "unresponsive": Semantic.FAILED,
    "failed": Semantic.FAILED,
}


def hint_line(text: str, *, theme: Theme | None = None) -> str:
    active_theme = theme or Theme()
    return f"  {active_theme.dim(f'Tip: {text}')}"


def story_table(
    stories: list[StoryDetail],
    *,
    theme: Theme | None = None,
    width: int | None = None,
) -> list[str]:
    if not stories:
        return []
    active_theme = theme or Theme()
    name_limit = story_name_limit(width)
    ordered = sorted(stories, key=lambda story: story.id)
    lines = [section_border("Stories", width=width, theme=active_theme)]
    header = _format_story_row(
        "ID",
        "Name",
        "State",
        "Worker",
        "Duration",
        "Retries",
        theme=active_theme,
        name_limit=name_limit,
        header=True,
    )
    lines.append(header)
    for story in ordered:
        worker = f"W{story.worker_id}" if story.worker_id is not None else "—"
        state = _style_state(story.display_state, active_theme)
        lines.append(
            _format_story_row(
                f"#{story.id}",
                truncate_text(story.title, name_limit),
                state,
                worker,
                story.duration,
                story.retries,
                theme=active_theme,
                name_limit=name_limit,
            )
        )
    return lines


def worker_table(
    workers: list[WorkerDetail],
    *,
    theme: Theme | None = None,
    width: int | None = None,
    healthy_count: int | None = None,
) -> list[str]:
    if not workers:
        return []
    active_theme = theme or Theme()
    healthy = healthy_count if healthy_count is not None else sum(
        1 for worker in workers if worker.display_health == "healthy"
    )
    context = f"{healthy}/{len(workers)} healthy"
    lines = [
        section_border(
            "Workers",
            context=context,
            context_semantic=Semantic.HEALTHY if healthy == len(workers) else Semantic.ACTIVE,
            width=width,
            theme=active_theme,
        )
    ]
    for worker in workers:
        assignment = (
            f"Story #{worker.assigned_story_id}"
            if worker.assigned_story_id is not None
            else "—"
        )
        health = _style_health(worker.display_health, active_theme)
        worker_id = active_theme.bold(f"W{worker.id}")
        lines.append(
            f"  {worker_id}   {health}   {assignment}   uptime {worker.uptime}"
        )
    return lines


def story_detail_sections(stories: list[StoryDetail], *, theme: Theme | None = None) -> list[str]:
    active_theme = theme or Theme()
    lines: list[str] = []
    for story in stories:
        if not story.events:
            continue
        lines.append(
            section_border(
                f"Story #{story.id}",
                context=story.display_state,
                context_semantic=_STATE_SEMANTICS.get(story.display_state, Semantic.DEFAULT),
                theme=active_theme,
            )
        )
        lines.extend(event_timeline(story.events, theme=active_theme))
    return lines


def worker_detail_sections(workers: list[WorkerDetail], *, theme: Theme | None = None) -> list[str]:
    active_theme = theme or Theme()
    lines: list[str] = []
    for worker in workers:
        if not worker.log_excerpt:
            continue
        lines.append(
            section_border(
                f"Worker W{worker.id}",
                context="logs",
                context_semantic=Semantic.SECONDARY,
                theme=active_theme,
            )
        )
        for entry in worker.log_excerpt:
            lines.append(f"  {active_theme.dim(entry)}")
    return lines


def event_timeline(events, *, theme: Theme | None = None) -> list[str]:
    active_theme = theme or Theme()
    lines: list[str] = []
    for event in events:
        timestamp = active_theme.dim(event.timestamp)
        lines.append(f"  {timestamp}  {event.text}")
    return lines


def _format_story_row(
    story_id: str,
    name: str,
    state: str,
    worker: str,
    duration: str,
    retries: str,
    *,
    theme: Theme,
    name_limit: int,
    header: bool = False,
) -> str:
    cols = _STORY_COLUMNS.copy()
    cols["name"] = name_limit
    if header:
        styled_id = theme.bold(story_id.rjust(cols["id"]))
        styled_name = theme.bold(name.ljust(cols["name"]))
        styled_state = theme.bold(state.ljust(cols["state"]))
        styled_worker = theme.bold(worker.ljust(cols["worker"]))
        styled_duration = theme.bold(duration.rjust(cols["duration"]))
        styled_retries = theme.bold(retries.rjust(cols["retries"]))
    else:
        styled_id = story_id.rjust(cols["id"])
        styled_name = name.ljust(cols["name"])
        styled_state = state if "\033[" in state else state.ljust(cols["state"])
        styled_worker = worker.ljust(cols["worker"])
        styled_duration = duration.rjust(cols["duration"])
        styled_retries = retries.rjust(cols["retries"])
    return (
        f"  {styled_id}  {styled_name}  {styled_state}  "
        f"{styled_worker}  {styled_duration}  {styled_retries}"
    )


def _style_state(display_state: str, theme: Theme) -> str:
    padded = display_state.ljust(_STORY_COLUMNS["state"])
    semantic = _STATE_SEMANTICS.get(display_state, Semantic.DEFAULT)
    return theme.semantic(padded, semantic)


def _style_health(display_health: str, theme: Theme) -> str:
    semantic = _HEALTH_SEMANTICS.get(display_health, Semantic.DEFAULT)
    return theme.semantic(display_health, semantic)
