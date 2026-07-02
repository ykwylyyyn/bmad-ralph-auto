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
    model: str | None = None
    raw_output: str = ""


def parse_worker_output(
    output: ClaudeOutput,
    *,
    output_format: str = "claude_json",
    model: str | None = None,
) -> ClaudeResult:
    if output_format == "plain":
        if output.exit_code == 0:
            return ClaudeResult(kind="success", result=output.stdout.strip(), model=model)
        return ClaudeResult(
            kind="failure",
            error=(output.stderr or output.stdout).strip(),
            model=model,
        )
    result = parse_claude_output(output)
    if model and result.model is None:
        return ClaudeResult(
            kind=result.kind,
            result=result.result,
            error=result.error,
            subtype=result.subtype,
            session_id=result.session_id,
            cost_usd=result.cost_usd,
            duration_ms=result.duration_ms,
            num_turns=result.num_turns,
            model=model,
            raw_output=result.raw_output,
        )
    return result


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
        model=raw.get("model") if isinstance(raw.get("model"), str) else None,
    )
