from __future__ import annotations

import sys
import threading
import time

from .theme import Semantic, Theme, visible_length
from .width import layout_width

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
PROGRESS_BAR_WIDTH = 30


def health_line(text: str, *, theme: Theme | None = None, semantic: Semantic = Semantic.DEFAULT) -> str:
    active_theme = theme or Theme()
    if semantic == Semantic.DEFAULT:
        return f"  {text}"
    return f"  {active_theme.semantic(text, semantic)}"


def progress_bar(
    completed: int,
    total: int,
    *,
    theme: Theme | None = None,
    label: str = "Stories",
) -> list[str]:
    active_theme = theme or Theme()
    percentage = 0 if total <= 0 else round((completed / total) * 100)
    filled = 0 if total <= 0 else round((completed / total) * PROGRESS_BAR_WIDTH)
    filled = min(PROGRESS_BAR_WIDTH, max(0, filled))
    empty = PROGRESS_BAR_WIDTH - filled
    bar = f"{active_theme.magenta('█' * filled)}{active_theme.dim('░' * empty)}"
    return [
        f"  {active_theme.bold(label)}",
        f"  {bar}  {percentage}% completed",
    ]


def summary_line(counts: dict[str, int], *, theme: Theme | None = None) -> str:
    active_theme = theme or Theme()
    order = [
        ("completed", active_theme.green),
        ("running", active_theme.yellow),
        ("retrying", active_theme.yellow),
        ("restarting", active_theme.yellow),
        ("diagnosing", active_theme.yellow),
        ("queued", active_theme.dim),
        ("blocked", active_theme.dim),
        ("failed", active_theme.red),
    ]
    segments: list[str] = []
    for name, styler in order:
        value = counts.get(name, 0)
        if value <= 0:
            continue
        segments.append(f"{active_theme.bold(str(value))} {styler(name)}")
    if not segments:
        return "  0 stories loaded"
    return "  " + "  ".join(segments)


def completion_summary(
    *,
    success_percent: int,
    self_healed: int,
    failed: int,
    runtime: str,
    worker_count: int,
    failed_stories: list[int],
    theme: Theme | None = None,
    width: int | None = None,
) -> list[str]:
    active_theme = theme or Theme()
    if success_percent >= 95:
        success_text = active_theme.green(f"Success: {success_percent}%")
    elif success_percent >= 80:
        success_text = active_theme.yellow(f"Success: {success_percent}%")
    else:
        success_text = active_theme.red(f"Success: {success_percent}%")

    healed_text = active_theme.yellow(f"{self_healed} self-healed")
    failed_text = active_theme.red(f"{failed} failed")
    lines = [
        section_border("Summary", width=width, theme=active_theme),
        f"  {success_text} — {healed_text}, {failed_text}",
        f"  Runtime: {runtime} across {active_theme.bold(str(worker_count))} workers",
    ]
    for story_id in failed_stories:
        command = active_theme.bold(f"ralph diagnose {story_id}")
        lines.append(
            f"  Failed: Story #{story_id} — run {command} for details"
        )
    return lines


def section_border(
    name: str,
    *,
    context: str | None = None,
    context_semantic: Semantic = Semantic.DEFAULT,
    width: int | None = None,
    theme: Theme | None = None,
) -> str:
    active_theme = theme or Theme()
    target_width = layout_width(width)

    marker = active_theme.magenta("※")
    styled_name = active_theme.bold(name)
    fill_char = active_theme.dim("═")

    left_plain = f"※ {name} "
    right_plain = f" {context} ※" if context else " ※"
    fill_count = target_width - len(left_plain) - len(right_plain)
    if fill_count < 1:
        fill_count = 1

    styled_context = (
        active_theme.semantic(context, context_semantic) if context is not None else ""
    )
    fill = fill_char * fill_count
    if context is None:
        return f"{marker} {styled_name} {fill} {marker}"
    return f"{marker} {styled_name} {fill} {styled_context} {marker}"


def error_message(
    description: str,
    *,
    suggestion: str | None = None,
    detail_lines: list[str] | None = None,
    theme: Theme | None = None,
) -> str:
    active_theme = theme or Theme()
    lines = [f"{active_theme.bold_red('Error:')} {description}"]
    for line in detail_lines or []:
        lines.append(f"  {line}")
    if suggestion:
        lines.append(f"  {active_theme.dim(suggestion)}")
    return "\n".join(lines)


class Spinner:
    """Braille spinner that completes with a green check or red cross."""

    def __init__(
        self,
        message: str,
        *,
        theme: Theme | None = None,
        stream: object | None = None,
        animate: bool | None = None,
        interval_secs: float = 0.1,
    ) -> None:
        self._message = message
        self._theme = theme or Theme()
        self._stream = stream or sys.stdout
        self._interval_secs = interval_secs
        self._animate = animate
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frame_index = 0
        self._started = False

    def __enter__(self) -> Spinner:
        self._started = True
        if self._should_animate():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="ralph-spinner", daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        if not self._started:
            return
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join()
            self._thread = None
        if exc_type is None:
            self._write_line(f"{self._theme.green('✓')} {self._message} done")
        else:
            self._write_line(f"{self._theme.red('✗')} {self._message} failed")

    def _should_animate(self) -> bool:
        if self._animate is not None:
            return self._animate
        is_tty = bool(getattr(self._stream, "isatty", lambda: False)())
        return is_tty and self._theme.use_color

    def _run(self) -> None:
        while not self._stop_event.is_set():
            frame = SPINNER_FRAMES[self._frame_index % len(SPINNER_FRAMES)]
            self._frame_index += 1
            self._write_inline(f"{frame} {self._message}")
            time.sleep(self._interval_secs)

    def _write_inline(self, text: str) -> None:
        write = getattr(self._stream, "write", None)
        flush = getattr(self._stream, "flush", None)
        if write is None:
            return
        write(f"\r{text}")
        if flush is not None:
            flush()

    def _write_line(self, text: str) -> None:
        write = getattr(self._stream, "write", None)
        flush = getattr(self._stream, "flush", None)
        if write is None:
            return
        if self._should_animate():
            padding = " " * max(0, visible_length(self._message) + 4)
            write(f"\r{padding}\r{text}\n")
        else:
            write(f"{text}\n")
        if flush is not None:
            flush()
