from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Self

from ralph.common.models import (
    DiagnosticReport,
    HealingAttempt,
    HealingLayer,
    PipelineState,
    Story,
    StoryState,
    WorkerHealth,
    WorkerState,
)
from ralph.pipeline.state import is_valid_transition

from .errors import (
    ConcurrentModificationError,
    InvalidTransitionError,
    StoryAssignmentError,
    StoryNotFoundError,
    WorkerNotFoundError,
)
from .schema import apply_schema

DEFAULT_HEALING_RETENTION_DAYS = 7
DEFAULT_HEALING_MAX_ROWS = 10_000


@dataclass(slots=True)
class WorkerRecord:
    id: int
    state: WorkerState
    health: WorkerHealth
    worktree_path: str
    pid: int | None = None
    backend: str | None = None
    model: str | None = None
    cost_usd: float | None = None


@dataclass(slots=True)
class PipelineSnapshot:
    stories: list[Story]
    workers: list[WorkerRecord]


class StateStore:
    """Synchronous SQLite persistence for pipeline state."""

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
        _ensure_story_columns(self._connection)
        _ensure_worker_columns(self._connection)
        _ensure_story_memory_table(self._connection)
        self._connection.commit()

    def is_wal_enabled(self) -> bool:
        row = self._connection.execute("PRAGMA journal_mode").fetchone()
        return row is not None and str(row[0]).lower() == "wal"

    def upsert_story(self, story: Story) -> Story:
        now = _now()
        criteria_json = json.dumps(story.acceptance_criteria)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO stories (
                    id, story_key, title, state, worker_id, acceptance_criteria, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    story_key = excluded.story_key,
                    title = excluded.title,
                    state = excluded.state,
                    worker_id = excluded.worker_id,
                    acceptance_criteria = excluded.acceptance_criteria,
                    updated_at = excluded.updated_at
                """,
                (
                    story.id,
                    story.key or None,
                    story.title,
                    story.state.value,
                    story.worker_id,
                    criteria_json,
                    now,
                    now,
                ),
            )
        return self.get_story(story.id)

    def replace_story_dependencies(self, dependencies: dict[int, list[int]]) -> None:
        with self._connection:
            self._connection.execute("DELETE FROM story_dependencies")
            for story_id, dep_ids in dependencies.items():
                for dep_id in dep_ids:
                    self._connection.execute(
                        """
                        INSERT INTO story_dependencies (story_id, depends_on_id)
                        VALUES (?, ?)
                        """,
                        (story_id, dep_id),
                    )

    def list_story_dependencies(self, story_id: int | None = None) -> dict[int, list[int]]:
        if story_id is None:
            rows = self._connection.execute(
                "SELECT story_id, depends_on_id FROM story_dependencies ORDER BY story_id, depends_on_id"
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT story_id, depends_on_id
                FROM story_dependencies
                WHERE story_id = ?
                ORDER BY depends_on_id
                """,
                (story_id,),
            ).fetchall()

        mapping: dict[int, list[int]] = {}
        for row in rows:
            mapping.setdefault(row["story_id"], []).append(row["depends_on_id"])
        return mapping

    def get_story(self, story_id: int) -> Story:
        row = self._connection.execute(
            """
            SELECT id, story_key, title, state, worker_id, acceptance_criteria
            FROM stories WHERE id = ?
            """,
            (story_id,),
        ).fetchone()
        if row is None:
            raise StoryNotFoundError(story_id)
        dependencies = self.list_story_dependencies(story_id).get(story_id, [])
        return _story_from_row(row, dependencies)

    def list_stories(self) -> list[Story]:
        rows = self._connection.execute(
            """
            SELECT id, story_key, title, state, worker_id, acceptance_criteria
            FROM stories ORDER BY id
            """
        ).fetchall()
        dependency_map = self.list_story_dependencies()
        return [_story_from_row(row, dependency_map.get(row["id"], [])) for row in rows]

    def transition_story_state(self, story_id: int, to_state: StoryState) -> Story:
        now = _now()
        with self._connection:
            row = self._connection.execute(
                "SELECT state FROM stories WHERE id = ?",
                (story_id,),
            ).fetchone()
            if row is None:
                raise StoryNotFoundError(story_id)

            from_state = StoryState(row["state"])
            if not is_valid_transition(from_state, to_state):
                raise InvalidTransitionError(story_id, from_state.value, to_state.value)

            cursor = self._connection.execute(
                """
                UPDATE stories
                SET state = ?, updated_at = ?
                WHERE id = ? AND state = ?
                """,
                (to_state.value, now, story_id, from_state.value),
            )
            if cursor.rowcount != 1:
                raise ConcurrentModificationError(story_id, from_state.value)

        return self.get_story(story_id)

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
            row = self._connection.execute(
                "SELECT state, worker_id FROM stories WHERE id = ?",
                (story_id,),
            ).fetchone()
            if row is None:
                raise StoryNotFoundError(story_id)

            from_state = StoryState(row["state"])
            if from_state != StoryState.QUEUED:
                raise StoryAssignmentError(story_id, f"story must be queued (current: {from_state.value})")

            worker = self._connection.execute(
                "SELECT id FROM workers WHERE id = ?",
                (worker_id,),
            ).fetchone()
            if worker is None:
                raise WorkerNotFoundError(worker_id)

            if not is_valid_transition(StoryState.QUEUED, StoryState.IN_PROGRESS):
                raise InvalidTransitionError(story_id, from_state.value, StoryState.IN_PROGRESS.value)

            cursor = self._connection.execute(
                """
                UPDATE stories
                SET state = ?, worker_id = ?, updated_at = ?
                WHERE id = ? AND state = ?
                """,
                (StoryState.IN_PROGRESS.value, worker_id, now, story_id, from_state.value),
            )
            if cursor.rowcount != 1:
                raise ConcurrentModificationError(story_id, from_state.value)

        return self.get_story(story_id)

    def rollback_story_assignment(self, story_id: int) -> Story:
        now = _now()
        with self._connection:
            row = self._connection.execute(
                "SELECT state FROM stories WHERE id = ?",
                (story_id,),
            ).fetchone()
            if row is None:
                raise StoryNotFoundError(story_id)

            from_state = StoryState(row["state"])
            if not is_valid_transition(from_state, StoryState.QUEUED):
                raise InvalidTransitionError(story_id, from_state.value, StoryState.QUEUED.value)

            cursor = self._connection.execute(
                """
                UPDATE stories
                SET state = ?, worker_id = NULL, updated_at = ?
                WHERE id = ? AND state = ?
                """,
                (StoryState.QUEUED.value, now, story_id, from_state.value),
            )
            if cursor.rowcount != 1:
                raise ConcurrentModificationError(story_id, from_state.value)
        return self.get_story(story_id)

    def clear_story_worker(self, story_id: int) -> Story:
        return self.set_story_worker(story_id, None)

    def set_story_worker(self, story_id: int, worker_id: int | None) -> Story:
        now = _now()
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE stories SET worker_id = ?, updated_at = ? WHERE id = ?",
                (worker_id, now, story_id),
            )
            if cursor.rowcount != 1:
                raise StoryNotFoundError(story_id)
        return self.get_story(story_id)

    def get_pipeline_state(self) -> PipelineState:
        row = self._connection.execute(
            "SELECT state FROM pipeline_state WHERE id = 1"
        ).fetchone()
        if row is None:
            return PipelineState.IDLE
        return PipelineState(row["state"])

    def set_pipeline_state(self, state: PipelineState) -> None:
        now = _now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO pipeline_state (id, state, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    updated_at = excluded.updated_at
                """,
                (state.value, now),
            )

    def record_pipeline_event(self, event_type: str, payload: dict[str, object] | None = None) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO pipeline_events (event_type, payload, created_at)
                VALUES (?, ?, ?)
                """,
                (event_type, json.dumps(payload or {}), _now()),
            )

    def list_pipeline_events(self, event_type: str | None = None) -> list[dict[str, object]]:
        if event_type is None:
            rows = self._connection.execute(
                "SELECT event_type, payload, created_at FROM pipeline_events ORDER BY id"
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT event_type, payload, created_at
                FROM pipeline_events
                WHERE event_type = ?
                ORDER BY id
                """,
                (event_type,),
            ).fetchall()
        events: list[dict[str, object]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            events.append(
                {
                    "event_type": row["event_type"],
                    "payload": payload,
                    "created_at": row["created_at"],
                }
            )
        return events

    def get_story_memory(self, story_id: int, key: str) -> object | None:
        row = self._connection.execute(
            """
            SELECT value_json
            FROM story_memory
            WHERE story_id = ? AND key = ?
            """,
            (story_id, key),
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["value_json"])
        except json.JSONDecodeError:
            return None

    def set_story_memory(self, story_id: int, key: str, value: object) -> None:
        now = _now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO story_memory (story_id, key, value_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(story_id, key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (story_id, key, json.dumps(value), now),
            )

    def delete_story_memory(self, story_id: int, key: str) -> None:
        with self._connection:
            self._connection.execute(
                "DELETE FROM story_memory WHERE story_id = ? AND key = ?",
                (story_id, key),
            )

    def upsert_worker(self, worker: WorkerRecord) -> WorkerRecord:
        now = _now()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO workers (
                    id, state, health, worktree_path, pid, backend, model, cost_usd,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    health = excluded.health,
                    worktree_path = excluded.worktree_path,
                    pid = excluded.pid,
                    backend = excluded.backend,
                    model = excluded.model,
                    cost_usd = excluded.cost_usd,
                    updated_at = excluded.updated_at
                """,
                (
                    worker.id,
                    worker.state.value,
                    worker.health.value,
                    worker.worktree_path,
                    worker.pid,
                    worker.backend,
                    worker.model,
                    worker.cost_usd,
                    now,
                    now,
                ),
            )
        return self.get_worker(worker.id)

    def get_worker(self, worker_id: int) -> WorkerRecord:
        row = self._connection.execute(
            """
            SELECT id, state, health, worktree_path, pid, backend, model, cost_usd
            FROM workers WHERE id = ?
            """,
            (worker_id,),
        ).fetchone()
        if row is None:
            raise WorkerNotFoundError(worker_id)
        return _worker_from_row(row)

    def list_workers(self) -> list[WorkerRecord]:
        rows = self._connection.execute(
            """
            SELECT id, state, health, worktree_path, pid, backend, model, cost_usd
            FROM workers ORDER BY id
            """
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

    def load_snapshot(self) -> PipelineSnapshot:
        return PipelineSnapshot(stories=self.list_stories(), workers=self.list_workers())

    def prune_healing_attempts(
        self,
        *,
        retention_days: int = DEFAULT_HEALING_RETENTION_DAYS,
        max_rows: int = DEFAULT_HEALING_MAX_ROWS,
    ) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        with self._connection:
            self._connection.execute(
                "DELETE FROM healing_attempts WHERE created_at < ?",
                (cutoff,),
            )
            deleted_by_age = self._connection.total_changes

            row = self._connection.execute("SELECT COUNT(*) FROM healing_attempts").fetchone()
            total = int(row[0]) if row is not None else 0
            if total > max_rows:
                overflow = total - max_rows
                self._connection.execute(
                    """
                    DELETE FROM healing_attempts
                    WHERE id IN (
                        SELECT id FROM healing_attempts
                        ORDER BY id ASC
                        LIMIT ?
                    )
                    """,
                    (overflow,),
                )
                deleted_by_age += self._connection.total_changes

        return deleted_by_age


def _story_from_row(row: sqlite3.Row, dependencies: list[int] | None = None) -> Story:
    criteria_raw = row["acceptance_criteria"] if "acceptance_criteria" in row.keys() else "[]"
    try:
        acceptance_criteria = json.loads(criteria_raw or "[]")
    except json.JSONDecodeError:
        acceptance_criteria = []
    if not isinstance(acceptance_criteria, list):
        acceptance_criteria = []

    story_key = row["story_key"] if "story_key" in row.keys() else ""
    return Story(
        id=row["id"],
        key=story_key or "",
        title=row["title"],
        state=StoryState(row["state"]),
        worker_id=row["worker_id"],
        dependencies=list(dependencies or []),
        acceptance_criteria=[str(item) for item in acceptance_criteria],
    )


def _worker_from_row(row: sqlite3.Row) -> WorkerRecord:
    keys = set(row.keys())
    return WorkerRecord(
        id=row["id"],
        state=WorkerState(row["state"]),
        health=WorkerHealth(row["health"]),
        worktree_path=row["worktree_path"],
        pid=row["pid"],
        backend=str(row["backend"]) if "backend" in keys and row["backend"] is not None else None,
        model=str(row["model"]) if "model" in keys and row["model"] is not None else None,
        cost_usd=float(row["cost_usd"]) if "cost_usd" in keys and row["cost_usd"] is not None else None,
    )


def _ensure_worker_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(workers)").fetchall()
    }
    if "backend" not in columns:
        connection.execute("ALTER TABLE workers ADD COLUMN backend TEXT")
    if "model" not in columns:
        connection.execute("ALTER TABLE workers ADD COLUMN model TEXT")
    if "cost_usd" not in columns:
        connection.execute("ALTER TABLE workers ADD COLUMN cost_usd REAL")


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


def _ensure_story_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(stories)").fetchall()
    }
    if "story_key" not in columns:
        connection.execute("ALTER TABLE stories ADD COLUMN story_key TEXT")
    if "acceptance_criteria" not in columns:
        connection.execute(
            "ALTER TABLE stories ADD COLUMN acceptance_criteria TEXT NOT NULL DEFAULT '[]'"
        )


def _ensure_story_memory_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS story_memory (
            story_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (story_id, key),
            FOREIGN KEY(story_id) REFERENCES stories(id)
        )
        """
    )
