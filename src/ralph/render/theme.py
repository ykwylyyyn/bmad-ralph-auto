from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
import re
import sys


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


class Semantic(StrEnum):
    HEALTHY = "healthy"
    ACTIVE = "active"
    FAILED = "failed"
    SECONDARY = "secondary"
    DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class Theme:
    use_color: bool = True

    def stylize(self, text: str, *codes: int) -> str:
        if not self.use_color or not codes:
            return text
        return f"\033[{';'.join(str(code) for code in codes)}m{text}\033[0m"

    def bold(self, text: str) -> str:
        return self.stylize(text, 1)

    def dim(self, text: str) -> str:
        return self.stylize(text, 2)

    def green(self, text: str) -> str:
        return self.stylize(text, 32)

    def yellow(self, text: str) -> str:
        return self.stylize(text, 33)

    def red(self, text: str) -> str:
        return self.stylize(text, 31)

    def magenta(self, text: str) -> str:
        return self.stylize(text, 35)

    def bold_red(self, text: str) -> str:
        return self.stylize(text, 1, 31)

    def semantic(self, text: str, semantic: Semantic) -> str:
        if semantic == Semantic.HEALTHY:
            return self.green(text)
        if semantic == Semantic.ACTIVE:
            return self.yellow(text)
        if semantic == Semantic.FAILED:
            return self.red(text)
        if semantic == Semantic.SECONDARY:
            return self.dim(text)
        return text


def resolve_theme(*, no_color: bool = False, stream: object | None = None) -> Theme:
    if no_color or os.environ.get("NO_COLOR"):
        return Theme(use_color=False)
    output = stream if stream is not None else sys.stdout
    is_tty = bool(getattr(output, "isatty", lambda: False)())
    if not is_tty:
        return Theme(use_color=False)
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return Theme(use_color=False)
    return Theme(use_color=True)


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def visible_length(text: str) -> int:
    return len(strip_ansi(text))
