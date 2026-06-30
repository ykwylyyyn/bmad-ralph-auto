from __future__ import annotations

import shutil


def detect_terminal_width(*, fallback: int = 80) -> int:
    try:
        return shutil.get_terminal_size(fallback=(fallback, 24)).columns
    except OSError:
        return fallback


def layout_width(term_width: int | None = None) -> int:
    width = detect_terminal_width() if term_width is None else term_width
    return max(80, min(width, 120))


def story_name_limit(term_width: int | None = None) -> int:
    width = detect_terminal_width() if term_width is None else term_width
    if width < 80:
        return 15
    if width < 100:
        return 20
    return 30


def truncate_text(text: str, limit: int) -> str:
    if limit < 1:
        return ""
    if len(text) <= limit:
        return text
    if limit == 1:
        return "…"
    return f"{text[: limit - 1]}…"
