from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from typing import Self

from ralph.common.models import HealingAttempt, HealingLayer, Story, StoryState, WorkerHealth, WorkerState
from ralph.pipeline.state import is_valid_transition

from .errors import ConcurrentModificationError, InvalidTransitionError, StoryNotFoundError, WorkerNotFoundError
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
        self._connection.commit()

    def is_wal_enabled(self) -> bool:
        row = self._connection.execute("PRAGMA journal_mode").fetchone()
        return row is not None and str(row[0]).lower() == "wal"

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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
