from __future__ import annotations

import os
import shlex


def resolve_claude_command(override: str | list[str] | None = None) -> list[str]:
    if isinstance(override, list):
        return list(override)
    if override is not None:
        return [override]

    command = [os.environ.get("RALPH_CLAUDE_BIN", "claude")]
    extra = os.environ.get("RALPH_CLAUDE_ARGS", "").strip()
    if extra:
        command.extend(shlex.split(extra, posix=os.name != "nt"))
    return command
