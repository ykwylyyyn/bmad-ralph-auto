from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Self

from ralph.common.models import (
    DiagnosticReport,
    HealingAttempt,
    HealingLayer,
    Story,
    StoryState,
    WorkerHealth,
    WorkerState,
)

from .errors import StoryNotFoundError, WorkerNotFoundError
from .schema import apply_schema


@dataclass(slots=True)
class WorkerRecord:
    id: int
    state: WorkerState
    health: WorkerHealth
    worktree_path: str
    pid: int | None = None


class StateStore:
    """Synchronous SQLite persistence for stories and healing attempts."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row

    @classmethod
    def open(cls, database_path: str | Path) -> Self:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=30.0)
        connection.execute("PRAGMA foreign_keys = ON")
        store = cls(connection)
        store.initialize()
        return store

    @classmethod
    def open_in_memory(cls) -> Self:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        connection.execute("PRAGMA foreign_keys = ON")
        store = cls(connection)
        store.initialize()
        return store

    def close(self) -> None:
        self._connection.close()

    def initialize(self) -> None:
        apply_schema(self._connection)
        self._connection.commit()

    def upsert_story(self, story: Story) -> Story:
        now = _now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO stories (id, title, state, worker_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    state = excluded.state,
                    worker_id = excluded.worker_id,
                    updated_at = excluded.updated_at
                """,
                (
                    story.id,
                    story.title,
                    story.state.value,
                    story.worker_id,
                    now,
                    now,
                ),
            )
        return self.get_story(story.id)

    def get_story(self, story_id: int) -> Story:
        row = self._connection.execute(
            "SELECT id, title, state, worker_id FROM stories WHERE id = ?",
            (story_id,),
        ).fetchone()
        if row is None:
            raise StoryNotFoundError(story_id)
        return _story_from_row(row)

    def list_stories(self) -> list[Story]:
        rows = self._connection.execute(
            "SELECT id, title, state, worker_id FROM stories ORDER BY id"
        ).fetchall()
        return [_story_from_row(row) for row in rows]

    def set_story_state(self, story_id: int, state: StoryState) -> Story:
        now = _now()
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE stories SET state = ?, updated_at = ? WHERE id = ?",
                (state.value, now, story_id),
            )
            if cursor.rowcount != 1:
                raise StoryNotFoundError(story_id)
        return self.get_story(story_id)

    def requeue_story(self, story_id: int) -> Story:
        now = _now()
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE stories
                SET state = ?, worker_id = NULL, updated_at = ?
                WHERE id = ?
                """,
                (StoryState.QUEUED.value, now, story_id),
            )
            if cursor.rowcount != 1:
                raise StoryNotFoundError(story_id)
        return self.get_story(story_id)

    def reset_healing_state(self, story_id: int) -> Story:
        with self._connection:
            self._connection.execute(
                "DELETE FROM healing_attempts WHERE story_id = ?",
                (story_id,),
            )
            self._connection.execute(
                "DELETE FROM diagnostic_reports WHERE story_id = ?",
                (story_id,),
            )
        return self.requeue_story(story_id)

    def assign_story_to_worker(self, story_id: int, worker_id: int) -> Story:
        now = _now()
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE stories
                SET state = ?, worker_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (StoryState.IN_PROGRESS.value, worker_id, now, story_id),
            )
            if cursor.rowcount != 1:
                raise StoryNotFoundError(story_id)
        return self.get_story(story_id)

    def upsert_worker(self, worker: WorkerRecord) -> WorkerRecord:
        now = _now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO workers (id, state, health, worktree_path, pid, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    health = excluded.health,
                    worktree_path = excluded.worktree_path,
                    pid = excluded.pid,
                    updated_at = excluded.updated_at
                """,
                (
                    worker.id,
                    worker.state.value,
                    worker.health.value,
                    worker.worktree_path,
                    worker.pid,
                    now,
                    now,
                ),
            )
        return self.get_worker(worker.id)

    def get_worker(self, worker_id: int) -> WorkerRecord:
        row = self._connection.execute(
            "SELECT id, state, health, worktree_path, pid FROM workers WHERE id = ?",
            (worker_id,),
        ).fetchone()
        if row is None:
            raise WorkerNotFoundError(worker_id)
        return _worker_from_row(row)

    def list_workers(self) -> list[WorkerRecord]:
        rows = self._connection.execute(
            "SELECT id, state, health, worktree_path, pid FROM workers ORDER BY id"
        ).fetchall()
        return [_worker_from_row(row) for row in rows]

    def record_healing_attempt(self, attempt: HealingAttempt) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO healing_attempts (story_id, layer, attempt, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    attempt.story_id,
                    attempt.layer.value,
                    attempt.attempt,
                    attempt.reason,
                    _now(),
                ),
            )

    def list_healing_attempts(self, story_id: int | None = None) -> list[HealingAttempt]:
        if story_id is None:
            rows = self._connection.execute(
                "SELECT story_id, layer, attempt, reason FROM healing_attempts ORDER BY id"
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT story_id, layer, attempt, reason
                FROM healing_attempts
                WHERE story_id = ?
                ORDER BY id
                """,
                (story_id,),
            ).fetchall()
        return [
            HealingAttempt(
                story_id=row["story_id"],
                layer=HealingLayer(row["layer"]),
                attempt=row["attempt"],
                reason=row["reason"],
            )
            for row in rows
        ]

    def count_healing_attempts(self, story_id: int, layer: HealingLayer) -> int:
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM healing_attempts
            WHERE story_id = ? AND layer = ? AND reason != 'self-healed'
            """,
            (story_id, layer.value),
        ).fetchone()
        return int(row["total"]) if row is not None else 0

    def mark_story_exhausted(self, story_id: int) -> Story:
        now = _now()
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE stories
                SET state = ?, worker_id = NULL, updated_at = ?
                WHERE id = ?
                """,
                (StoryState.FAILED.value, now, story_id),
            )
            if cursor.rowcount != 1:
                raise StoryNotFoundError(story_id)
        return self.get_story(story_id)

    def save_diagnostic_report(self, report: DiagnosticReport) -> DiagnosticReport:
        now = _now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO diagnostic_reports (
                    story_id, root_cause, recommendation, suggested_fix, analysis_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(story_id) DO UPDATE SET
                    root_cause = excluded.root_cause,
                    recommendation = excluded.recommendation,
                    suggested_fix = excluded.suggested_fix,
                    analysis_json = excluded.analysis_json,
                    created_at = excluded.created_at
                """,
                (
                    report.story_id,
                    report.root_cause,
                    report.recommendation,
                    report.suggested_fix,
                    json.dumps(report.analysis),
                    now,
                ),
            )
        return self.get_diagnostic_report(report.story_id)

    def get_diagnostic_report(self, story_id: int) -> DiagnosticReport:
        row = self._connection.execute(
            """
            SELECT id, story_id, root_cause, recommendation, suggested_fix, analysis_json
            FROM diagnostic_reports
            WHERE story_id = ?
            """,
            (story_id,),
        ).fetchone()
        if row is None:
            raise StoryNotFoundError(story_id)
        return _diagnostic_report_from_row(row)


def _story_from_row(row: sqlite3.Row) -> Story:
    return Story(
        id=row["id"],
        title=row["title"],
        state=StoryState(row["state"]),
        worker_id=row["worker_id"],
    )


def _worker_from_row(row: sqlite3.Row) -> WorkerRecord:
    return WorkerRecord(
        id=row["id"],
        state=WorkerState(row["state"]),
        health=WorkerHealth(row["health"]),
        worktree_path=row["worktree_path"],
        pid=row["pid"],
    )


def _diagnostic_report_from_row(row: sqlite3.Row) -> DiagnosticReport:
    try:
        analysis = json.loads(row["analysis_json"] or "{}")
    except json.JSONDecodeError:
        analysis = {}
    if not isinstance(analysis, dict):
        analysis = {}
    return DiagnosticReport(
        id=int(row["id"]),
        story_id=int(row["story_id"]),
        root_cause=str(row["root_cause"]),
        recommendation=str(row["recommendation"]),
        suggested_fix=str(row["suggested_fix"]),
        analysis=analysis,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
