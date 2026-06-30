from __future__ import annotations

from ralph.render.components import section_border
from ralph.render.theme import Semantic, Theme
from ralph.render.width import layout_width

from .snapshot import DiagnoseSnapshot


def render_diagnose(snapshot: DiagnoseSnapshot, *, theme: Theme | None = None, width: int | None = None) -> str:
    active_theme = theme or Theme()
    target_width = layout_width(width)
    lines: list[str] = []

    context = f"Story #{snapshot.story_id}: {snapshot.title}"
    lines.append(
        section_border(
            "Diagnose",
            context=context,
            context_semantic=Semantic.FAILED if snapshot.exhausted else Semantic.ACTIVE,
            width=target_width,
            theme=active_theme,
        )
    )

    state_label = (
        "failed (exhausted — all 3 healing layers attempted)"
        if snapshot.exhausted
        else "failed"
    )
    lines.append(f"  State: {active_theme.red(state_label)}")
    lines.append(f"  Duration: {snapshot.duration}")
    lines.append(f"  Retries: {snapshot.retry_count} across workers")

    if snapshot.events:
        lines.append(section_border("Timeline", width=target_width, theme=active_theme))
        lines.extend(diagnose_event_timeline(snapshot.events, theme=active_theme))

    lines.append(section_border("Recommendation", width=target_width, theme=active_theme))
    lines.append(f"  Root cause: {snapshot.root_cause}")
    lines.append(f"  Recommendation: {snapshot.recommendation}")
    lines.append(f"  Suggested fix: {active_theme.bold(snapshot.suggested_fix)}")

    lines.append(section_border("Context", width=target_width, theme=active_theme))
    lines.extend(_machine_readable_context(snapshot))

    return "\n".join(lines)


def diagnose_event_timeline(events, *, theme: Theme | None = None) -> list[str]:
    active_theme = theme or Theme()
    lines: list[str] = []
    for event in events:
        timestamp = active_theme.dim(event.timestamp)
        layer = active_theme.bold(f"{event.layer_label}:")
        lines.append(f"  {timestamp}  {layer} {event.description}")
    return lines


def _machine_readable_context(snapshot: DiagnoseSnapshot) -> list[str]:
    lines = [
        f"  story_id: {snapshot.story_id}",
        f"  title: {snapshot.title}",
        f"  state: failed",
        f"  exhausted: {'true' if snapshot.exhausted else 'false'}",
        f"  retry_count: {snapshot.retry_count}",
        f"  suggested_fix: {snapshot.suggested_fix}",
    ]
    layers = snapshot.analysis.get("healing_layers_attempted")
    if isinstance(layers, list):
        lines.append(f"  healing_layers: {','.join(str(item) for item in layers)}")
    return lines
