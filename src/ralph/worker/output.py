from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from .process import ClaudeOutput


@dataclass(frozen=True, slots=True)
class ClaudeResult:
    kind: Literal["success", "failure", "parse_error"]
    result: str = ""
    error: str = ""
    subtype: str | None = None
    session_id: str | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    num_turns: int | None = None
    raw_output: str = ""


def parse_claude_output(output: ClaudeOutput) -> ClaudeResult:
    if output.exit_code != 0 and not output.stdout.strip():
        return ClaudeResult(kind="failure", error=output.stderr)

    try:
        raw = json.loads(output.stdout)
    except json.JSONDecodeError as exc:
        return ClaudeResult(kind="parse_error", error=str(exc), raw_output=output.stdout)

    subtype = raw.get("subtype")
    is_error = bool(raw.get("is_error", False))
    if is_error or subtype != "success":
        return ClaudeResult(kind="failure", error=raw.get("result", ""), subtype=subtype)

    return ClaudeResult(
        kind="success",
        result=raw.get("result", ""),
        session_id=raw.get("session_id"),
        cost_usd=raw.get("cost_usd"),
        duration_ms=raw.get("duration_ms"),
        num_turns=raw.get("num_turns"),
    )
