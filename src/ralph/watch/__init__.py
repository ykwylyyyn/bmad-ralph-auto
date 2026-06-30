from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ralph.render import Theme, error_message
from ralph.status import load_status_snapshot, render_status

DEFAULT_REFRESH_SECS = 2.0
_CLEAR_SCREEN = "\033[2J\033[H"
_SHOW_CURSOR = "\033[?25h"
_HIDE_CURSOR = "\033[?25l"


class WatchExitKind(StrEnum):
    STOPPED = "stopped"
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True, slots=True)
class WatchResult:
    kind: WatchExitKind
    frames_rendered: int


def run_watch(
    project_dir: str | Path,
    *,
    theme: Theme,
    detail: bool = False,
    refresh_secs: float = DEFAULT_REFRESH_SECS,
    max_frames: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    load_snapshot=load_status_snapshot,
    write_stream=None,
) -> WatchResult | None:
    """Render a live-refreshed status dashboard until the daemon stops or the user interrupts."""
    root = Path(project_dir).resolve()
    stream = write_stream or sys.stdout

    snapshot = load_snapshot(root, detail=detail)
    if snapshot is None:
        print(
            error_message(
                "No running daemon found",
                suggestion="Start Ralph first: ralph start",
                theme=theme,
            ),
            file=stream,
        )
        return None

    frames = 0
    try:
        if stream.isatty():
            stream.write(_HIDE_CURSOR)
            stream.flush()

        while True:
            snapshot = load_snapshot(root, detail=detail)
            if snapshot is None:
                return WatchResult(kind=WatchExitKind.STOPPED, frames_rendered=frames)

            if stream.isatty():
                stream.write(_CLEAR_SCREEN)
            stream.write(
                render_status(
                    snapshot,
                    theme=theme,
                    project_dir=root,
                    detail=detail,
                )
            )
            stream.write(_watch_footer(refresh_secs, theme=theme))
            stream.flush()
            frames += 1

            if max_frames is not None and frames >= max_frames:
                return WatchResult(kind=WatchExitKind.COMPLETE, frames_rendered=frames)

            if snapshot.is_complete:
                return WatchResult(kind=WatchExitKind.COMPLETE, frames_rendered=frames)

            sleep_fn(refresh_secs)
    except KeyboardInterrupt:
        return WatchResult(kind=WatchExitKind.INTERRUPTED, frames_rendered=frames)
    finally:
        if stream.isatty():
            stream.write(_SHOW_CURSOR)
            stream.flush()


def _watch_footer(refresh_secs: float, *, theme: Theme) -> str:
    interval = f"{refresh_secs:g}"
    hint = f"Refreshing every {interval}s — Ctrl+C to exit"
    return f"\n\n{theme.dim(hint)}\n"
