from __future__ import annotations

from dataclasses import dataclass, field
import os
import sqlite3
from pathlib import Path

from ralph.common.models import StoryState
from ralph.daemon import RuntimePaths, read_status

_HEALING_LAYER_LABELS = {
    "step_retry": "retrying",
    "worker_restart": "restarting",
    "diagnose": "diagnosing",
}


@dataclass(frozen=True, slots=True)
class StoryCounts:
    completed: int = 0
    running: int = 0
    retrying: int = 0
    restarting: int = 0
    diagnosing: int = 0
    queued: int = 0
    blocked: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "completed": self.completed,
            "running": self.running,
            "retrying": self.retrying,
            "restarting": self.restarting,
            "diagnosing": self.diagnosing,
            "queued": self.queued,
            "blocked": self.blocked,
            "failed": self.failed,
        }

    @property
    def total(self) -> int:
        return sum(self.as_dict().values())


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    daemon_running: bool
    health_label: str
    started_at: str | None
    heartbeat_at: str | None
    max_workers: int
    active_workers: int
    story_counts: StoryCounts
    failed_story_ids: list[int] = field(default_factory=list)
    self_healed_count: int = 0
    recovery_story_count: int = 0

    @property
    def total_stories(self) -> int:
        return self.story_counts.total

    @property
    def is_complete(self) -> bool:
        if self.total_stories == 0:
            return False
        terminal = self.story_counts.completed + self.story_counts.failed
        return terminal == self.total_stories

    @property
    def success_percent(self) -> int:
        if self.total_stories == 0:
            return 0
        return round((self.story_counts.completed / self.total_stories) * 100)


def load_status_snapshot(project_dir: str | Path) -> StatusSnapshot | None:
    paths = RuntimePaths(Path(project_dir).resolve())
    daemon = read_status(paths.project_dir)
    if daemon.state != "running":
        return None
    if daemon.pid is not None and not _pid_exists(daemon.pid):
        return None

    if not paths.database_file.exists():
        return _empty_snapshot(daemon, active_workers=0)

    connection = sqlite3.connect(paths.database_file)
    connection.row_factory = sqlite3.Row
    try:
        story_rows = connection.execute(
            "SELECT id, state FROM stories ORDER BY id"
        ).fetchall()
        worker_rows = connection.execute(
            "SELECT id, state FROM workers ORDER BY id"
        ).fetchall()
        healing_rows = connection.execute(
            """
            SELECT story_id, layer, attempt, created_at
            FROM healing_attempts
            ORDER BY id
            """
        ).fetchall()
    finally:
        connection.close()

    return _build_snapshot(daemon, story_rows, worker_rows, healing_rows)


def _empty_snapshot(daemon, *, active_workers: int) -> StatusSnapshot:
    return StatusSnapshot(
        daemon_running=True,
        health_label="healthy",
        started_at=daemon.started_at,
        heartbeat_at=daemon.heartbeat_at,
        max_workers=daemon.max_workers,
        active_workers=active_workers,
        story_counts=StoryCounts(),
    )


def _build_snapshot(daemon, story_rows, worker_rows, healing_rows) -> StatusSnapshot:
    latest_healing: dict[int, str] = {}
    healing_count_by_story: dict[int, int] = {}
    for row in healing_rows:
        story_id = int(row["story_id"])
        healing_count_by_story[story_id] = healing_count_by_story.get(story_id, 0) + 1
        latest_healing[story_id] = str(row["layer"])

    counts = StoryCounts()
    failed_story_ids: list[int] = []
    self_healed = 0
    recovery_story_count = 0

    for row in story_rows:
        story_id = int(row["id"])
        state = StoryState(str(row["state"]))
        healing_label = _HEALING_LAYER_LABELS.get(latest_healing.get(story_id, ""))

        if state == StoryState.DONE:
            counts = _increment(counts, "completed")
            if healing_count_by_story.get(story_id, 0) > 0:
                self_healed += 1
            continue
        if state == StoryState.FAILED:
            counts = _increment(counts, "failed")
            failed_story_ids.append(story_id)
            continue
        if healing_label:
            counts = _increment(counts, healing_label)
            recovery_story_count += 1
            continue
        if state == StoryState.QUEUED:
            counts = _increment(counts, "queued")
        elif state == StoryState.BLOCKED:
            counts = _increment(counts, "blocked")
        elif state in {StoryState.IN_PROGRESS, StoryState.IN_REVIEW}:
            counts = _increment(counts, "running")

    active_workers = sum(
        1 for row in worker_rows if str(row["state"]) in {"running", "starting"}
    )
    health_label = _derive_health_label(counts, recovery_story_count)

    return StatusSnapshot(
        daemon_running=True,
        health_label=health_label,
        started_at=daemon.started_at,
        heartbeat_at=daemon.heartbeat_at,
        max_workers=daemon.max_workers,
        active_workers=active_workers,
        story_counts=counts,
        failed_story_ids=failed_story_ids,
        self_healed_count=self_healed,
        recovery_story_count=recovery_story_count,
    )


def _derive_health_label(counts: StoryCounts, recovery_story_count: int) -> str:
    if counts.total == 0:
        return "healthy"
    if counts.completed + counts.failed == counts.total:
        return "complete"
    if recovery_story_count > 0 or counts.retrying or counts.restarting or counts.diagnosing:
        return "healing"
    if counts.failed > 0 and counts.running == 0 and counts.queued == 0:
        return "error"
    return "healthy"


def _increment(counts: StoryCounts, field_name: str) -> StoryCounts:
    data = counts.as_dict()
    data[field_name] = data.get(field_name, 0) + 1
    return StoryCounts(**data)


def _pid_exists(pid: int) -> bool:
    if pid < 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True
