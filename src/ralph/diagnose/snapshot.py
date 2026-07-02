from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
import sqlite3
from pathlib import Path

from ralph.common.db.store import StateStore
from ralph.common.models import StoryState
from ralph.daemon import RuntimePaths
from ralph.render.timefmt import format_duration_between, parse_timestamp

_LAYER_DISPLAY = {
    "step_retry": "Layer 1",
    "worker_restart": "Layer 2",
    "diagnose": "Layer 3",
}


class DiagnoseLoadErrorKind(StrEnum):
    STORY_NOT_FOUND = "story_not_found"
    NO_FAILED_STORIES = "no_failed_stories"


@dataclass(frozen=True, slots=True)
class DiagnoseLoadError:
    kind: DiagnoseLoadErrorKind
    story_id: int | None = None


@dataclass(frozen=True, slots=True)
class DiagnoseEvent:
    timestamp: str
    layer_label: str
    description: str


@dataclass(frozen=True, slots=True)
class DiagnoseSnapshot:
    story_id: int
    title: str
    duration: str
    retry_count: int
    exhausted: bool
    root_cause: str
    recommendation: str
    suggested_fix: str
    events: list[DiagnoseEvent] = field(default_factory=list)
    analysis: dict[str, object] = field(default_factory=dict)


def list_failed_story_ids(project_dir: str | Path) -> list[int]:
    paths = RuntimePaths(Path(project_dir).resolve())
    if not paths.database_file.exists():
        return []

    store = StateStore.open(paths.database_file)
    try:
        return [story.id for story in store.list_stories() if story.state == StoryState.FAILED]
    finally:
        store.close()


def load_diagnose_snapshot(project_dir: str | Path, story_id: int) -> DiagnoseSnapshot | DiagnoseLoadError:
    paths = RuntimePaths(Path(project_dir).resolve())
    if not paths.database_file.exists():
        return DiagnoseLoadError(kind=DiagnoseLoadErrorKind.STORY_NOT_FOUND, story_id=story_id)

    connection = sqlite3.connect(paths.database_file)
    connection.row_factory = sqlite3.Row
    try:
        story_row = connection.execute(
            """
            SELECT id, title, state, worker_id, created_at, updated_at
            FROM stories
            WHERE id = ?
            """,
            (story_id,),
        ).fetchone()
        if story_row is None:
            return DiagnoseLoadError(kind=DiagnoseLoadErrorKind.STORY_NOT_FOUND, story_id=story_id)

        healing_rows = connection.execute(
            """
            SELECT layer, attempt, reason, created_at
            FROM healing_attempts
            WHERE story_id = ?
            ORDER BY id
            """,
            (story_id,),
        ).fetchall()

        report_row = connection.execute(
            """
            SELECT root_cause, recommendation, suggested_fix, analysis_json
            FROM diagnostic_reports
            WHERE story_id = ?
            """,
            (story_id,),
        ).fetchone()

        verification_rows = connection.execute(
            """
            SELECT payload, created_at
            FROM pipeline_events
            WHERE event_type = 'verification_failed'
              AND json_extract(payload, '$.story_id') = ?
            ORDER BY id
            """,
            (story_id,),
        ).fetchall()
    finally:
        connection.close()

    state = StoryState(str(story_row["state"]))
    duration = format_duration_between(
        str(story_row["created_at"]),
        str(story_row["updated_at"]),
    )
    retry_count = len([row for row in healing_rows if str(row["reason"]) != "self-healed"])
    layers_attempted = {str(row["layer"]) for row in healing_rows}
    exhausted = state == StoryState.FAILED and {
        "step_retry",
        "worker_restart",
        "diagnose",
    }.issubset(layers_attempted)

    if report_row is not None:
        try:
            analysis = json.loads(report_row["analysis_json"] or "{}")
        except json.JSONDecodeError:
            analysis = {}
        if not isinstance(analysis, dict):
            analysis = {}
        root_cause = str(report_row["root_cause"])
        recommendation = str(report_row["recommendation"])
        suggested_fix = str(report_row["suggested_fix"])
    else:
        root_cause = f"Story #{story_id} failed without a stored diagnostic report."
        recommendation = "Review healing history and worker logs before re-feeding the story."
        suggested_fix = f"ralph retry {story_id}"
        analysis = {}

    return DiagnoseSnapshot(
        story_id=story_id,
        title=str(story_row["title"]),
        duration=duration if duration != "0s" else "—",
        retry_count=retry_count,
        exhausted=exhausted,
        root_cause=root_cause,
        recommendation=recommendation,
        suggested_fix=suggested_fix,
        events=_build_events(healing_rows, verification_rows),
        analysis=analysis,
    )


def _build_events(
    healing_rows: list[sqlite3.Row],
    verification_rows: list[sqlite3.Row] | None = None,
) -> list[DiagnoseEvent]:
    events: list[tuple[str, DiagnoseEvent]] = []
    for row in healing_rows:
        layer = str(row["layer"])
        layer_label = _LAYER_DISPLAY.get(layer, layer)
        reason = str(row["reason"])
        attempt = int(row["attempt"])
        if reason == "self-healed":
            description = "self-healed"
        elif reason == "diagnose flow triggered":
            description = "diagnose flow triggered"
        elif reason.startswith("old_worker_id="):
            description = f"worker restart ({reason})"
        else:
            description = f"{reason} (attempt {attempt})"
        created_at = str(row["created_at"])
        events.append(
            (
                created_at,
                DiagnoseEvent(
                    timestamp=_format_event_time(created_at),
                    layer_label=layer_label,
                    description=description,
                ),
            )
        )

    for row in verification_rows or []:
        try:
            payload = json.loads(row["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        created_at = str(row["created_at"])
        events.append(
            (
                created_at,
                DiagnoseEvent(
                    timestamp=_format_event_time(created_at),
                    layer_label="Verifier",
                    description=_verification_description(payload),
                ),
            )
        )

    events.sort(key=lambda item: item[0])
    return [event for _created_at, event in events]


def _verification_description(payload: dict[str, object]) -> str:
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        first = failures[0]
        if isinstance(first, dict):
            command = str(first.get("command", "?"))
            exit_code = first.get("exit_code", "?")
            stderr = str(first.get("stderr", "")).strip()
            excerpt = "\n".join(stderr.splitlines()[-5:]) if stderr else ""
            description = f"{command} (exit {exit_code})"
            if excerpt:
                description = f"{description} — {excerpt}"
            return description
    summary = payload.get("summary")
    if summary:
        return str(summary)
    return "verification failed"


def _format_event_time(value: str) -> str:
    parsed = parse_timestamp(value)
    if parsed is None:
        return "—"
    return parsed.strftime("%H:%M")
