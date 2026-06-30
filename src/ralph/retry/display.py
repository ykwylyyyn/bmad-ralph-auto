from __future__ import annotations

from ralph.render.components import section_border
from ralph.render.theme import Semantic, Theme
from ralph.render.width import layout_width
from ralph.status.tables import hint_line

from .service import RetryResult


def render_retry_confirmation(result: RetryResult, *, theme: Theme | None = None, width: int | None = None) -> str:
    active_theme = theme or Theme()
    target_width = layout_width(width)
    context = f"Story #{result.story_id}: {result.title}"
    lines = [
        section_border(
            "Retry",
            context=context,
            context_semantic=Semantic.ACTIVE,
            width=target_width,
            theme=active_theme,
        ),
        f"  {active_theme.yellow('retrying')} — story re-queued with fresh healing state",
        f"  Worker: {result.worker_assignment}",
        hint_line("ralph status to monitor progress", theme=active_theme),
    ]
    return "\n".join(lines)
