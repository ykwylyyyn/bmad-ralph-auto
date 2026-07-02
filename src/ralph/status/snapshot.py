from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import sqlite3
import tomllib
from pathlib import Path

from ralph.common.models import StoryState
from ralph.daemon import RuntimePaths, read_status
from ralph.render.timefmt import format_duration_between, parse_timestamp

_HEALING_LAYER_LABELS = {
    "step_retry": "retrying",
    "worker_restart": "restarting",
    "diagnose": "diagnosing",
}

_LAYER_DISPLAY = {
    "step_retry": "Layer 1",
    "worker_restart": "Layer 2",
    "diagnose": "Layer 3",
}

_STATE_DISPLAY = {
    StoryState.DONE: "completed",
    StoryState.IN_PROGRESS: "running",
    StoryState.VERIFYING: "verifying",
    StoryState.IN_REVIEW: "running",
    StoryState.QUEUED: "queued",
    StoryState.BLOCKED: "blocked",
    StoryState.FAILED: "failed",
}

DEFAULT_HINT_THRESHOLD = 5


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
class StoryEvent:
    timestamp: str
    text: str


@dataclass(frozen=True, slots=True)
class StoryDetail:
    id: int
    title: str
    display_state: str
    worker_id: int | None
    duration: str
    retries: str
    events: list[StoryEvent] = field(default_factory=list)
    backend: str | None = None
    model: str | None = None
    cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class WorkerDetail:
    id: int
    display_health: str
    assigned_story_id: int | None
    uptime: str
    log_excerpt: list[str] = field(default_factory=list)
    backend: str | None = None
    model: str | None = None


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    daemon_running: bool
    health_label: str
    started_at: str | None
    heartbeat_at: str | None
    max_workers: int
    active_workers: int
    story_counts: StoryCounts
    stories: list[StoryDetail] = field(default_factory=list)
    workers: list[WorkerDetail] = field(default_factory=list)
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

    @property
    def healthy_worker_count(self) -> int:
        return sum(1 for worker in self.workers if worker.display_health == "healthy")


def load_status_snapshot(
    project_dir: str | Path,
    *,
    detail: bool = False,
) -> StatusSnapshot | None:
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
            """
            SELECT id, title, state, worker_id, created_at, updated_at
            FROM stories
            ORDER BY id
            """
        ).fetchall()
        worker_rows = connection.execute(
            """
            SELECT id, state, health, backend, model, created_at, updated_at
            FROM workers
            ORDER BY id
            """
        ).fetchall()
        healing_rows = connection.execute(
            """
            SELECT story_id, layer, attempt, reason, created_at
            FROM healing_attempts
            ORDER BY id
            """
        ).fetchall()
        memory_rows = connection.execute(
            """
            SELECT story_id, key, value_json
            FROM story_memory
            WHERE key IN ('run.backend', 'run.model', 'run.cost_usd')
            """
        ).fetchall()
    finally:
        connection.close()

    return _build_snapshot(
        daemon,
        story_rows,
        worker_rows,
        healing_rows,
        memory_rows=memory_rows,
        logs_dir=paths.logs_dir if detail else None,
    )


def should_show_status_hint(project_dir: str | Path, *, threshold: int = DEFAULT_HINT_THRESHOLD) -> bool:
    if not _hints_enabled(project_dir):
        return False
    return record_status_invocation(project_dir) <= threshold


def record_status_invocation(project_dir: str | Path) -> int:
    paths = RuntimePaths(Path(project_dir).resolve())
    paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    state_file = paths.runtime_dir / "hint-state.json"
    data: dict[str, int] = {}
    if state_file.exists():
        try:
            loaded = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = {str(key): int(value) for key, value in loaded.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            data = {}
    count = data.get("status", 0) + 1
    data["status"] = count
    state_file.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return count


def _hints_enabled(project_dir: str | Path) -> bool:
    config_path = Path(project_dir).resolve() / "ralph.toml"
    if not config_path.exists():
        return True
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return True
    hints = data.get("hints")
    if hints is False:
        return False
    return True


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


def _build_snapshot(
    daemon,
    story_rows,
    worker_rows,
    healing_rows,
    *,
    memory_rows: list[sqlite3.Row] | None = None,
    logs_dir: Path | None = None,
) -> StatusSnapshot:
    healing_by_story: dict[int, list[sqlite3.Row]] = {}
    latest_healing: dict[int, str] = {}
    healing_count_by_story: dict[int, int] = {}
    for row in healing_rows:
        story_id = int(row["story_id"])
        healing_count_by_story[story_id] = healing_count_by_story.get(story_id, 0) + 1
        latest_healing[story_id] = str(row["layer"])
        healing_by_story.setdefault(story_id, []).append(row)

    run_metadata = _parse_run_metadata(memory_rows or [])

    counts = StoryCounts()
    failed_story_ids: list[int] = []
    self_healed = 0
    recovery_story_count = 0
    stories: list[StoryDetail] = []

    for row in story_rows:
        story_id = int(row["id"])
        state = StoryState(str(row["state"]))
        healing_label = _HEALING_LAYER_LABELS.get(latest_healing.get(story_id, ""))
        display_state = healing_label or _STATE_DISPLAY.get(state, state.value)
        retries_count = healing_count_by_story.get(story_id, 0)
        exhausted = state == StoryState.FAILED and retries_count > 0
        retries = f"{retries_count} (exhausted)" if exhausted else str(retries_count)
        duration = _story_duration(
            str(row["created_at"]),
            str(row["updated_at"]),
            state,
            daemon.heartbeat_at,
        )
        events = _story_events(story_id, healing_by_story.get(story_id, []), row)
        run_info = run_metadata.get(story_id, {})
        backend = run_info.get("backend")
        model = run_info.get("model")
        cost_usd = run_info.get("cost_usd")
        if backend or model or cost_usd is not None:
            cost_text = f"${cost_usd:.4f}" if isinstance(cost_usd, (int, float)) else "—"
            events.append(
                StoryEvent(
                    timestamp="—",
                    text=(
                        f"Backend: {backend or '—'} | "
                        f"Model: {model or '—'} | "
                        f"Cost: {cost_text}"
                    ),
                )
            )
        stories.append(
            StoryDetail(
                id=story_id,
                title=str(row["title"]),
                display_state=display_state,
                worker_id=row["worker_id"],
                duration=duration,
                retries=retries,
                events=events,
                backend=str(backend) if backend else None,
                model=str(model) if model else None,
                cost_usd=float(cost_usd) if isinstance(cost_usd, (int, float)) else None,
            )
        )

        if state == StoryState.DONE:
            counts = _increment(counts, "completed")
            if retries_count > 0:
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
        elif state in {StoryState.IN_PROGRESS, StoryState.IN_REVIEW, StoryState.VERIFYING}:
            counts = _increment(counts, "running")

    worker_assignments = {
        int(row["worker_id"]): int(row["id"])
        for row in story_rows
        if row["worker_id"] is not None
    }
    workers: list[WorkerDetail] = []
    for row in worker_rows:
        worker_id = int(row["id"])
        health = str(row["health"])
        worker_state = str(row["state"])
        display_health = _worker_display_health(health, worker_state)
        uptime = format_duration_between(str(row["created_at"]), daemon.heartbeat_at)
        log_excerpt = _read_log_excerpt(logs_dir, worker_id) if logs_dir is not None else []
        backend = str(row["backend"]) if row["backend"] is not None else None
        model = str(row["model"]) if row["model"] is not None else None
        workers.append(
            WorkerDetail(
                id=worker_id,
                display_health=display_health,
                assigned_story_id=worker_assignments.get(worker_id),
                uptime=uptime,
                log_excerpt=log_excerpt,
                backend=backend,
                model=model,
            )
        )

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
        stories=stories,
        workers=workers,
        failed_story_ids=failed_story_ids,
        self_healed_count=self_healed,
        recovery_story_count=recovery_story_count,
    )


def _parse_run_metadata(rows: list[sqlite3.Row]) -> dict[int, dict[str, object]]:
    metadata: dict[int, dict[str, object]] = {}
    for row in rows:
        story_id = int(row["story_id"])
        key = str(row["key"])
        try:
            value = json.loads(row["value_json"])
        except json.JSONDecodeError:
            continue
        entry = metadata.setdefault(story_id, {})
        if key == "run.backend":
            entry["backend"] = value
        elif key == "run.model":
            entry["model"] = value
        elif key == "run.cost_usd":
            entry["cost_usd"] = value
    return metadata


def _story_duration(created_at: str, updated_at: str, state: StoryState, heartbeat_at: str | None) -> str:
    if state == StoryState.QUEUED:
        return "—"
    end = heartbeat_at if state in {StoryState.IN_PROGRESS, StoryState.IN_REVIEW, StoryState.VERIFYING} else updated_at
    duration = format_duration_between(created_at, end)
    return duration if duration != "0s" else "—"


def _story_events(story_id: int, healing_rows: list[sqlite3.Row], story_row: sqlite3.Row) -> list[StoryEvent]:
    events: list[StoryEvent] = []
    worker_id = story_row["worker_id"]
    if worker_id is not None:
        events.append(StoryEvent(timestamp="—", text=f"Assigned to W{worker_id}"))
    for row in healing_rows:
        layer = str(row["layer"])
        layer_label = _LAYER_DISPLAY.get(layer, layer)
        timestamp = _format_event_time(str(row["created_at"]))
        events.append(
            StoryEvent(
                timestamp=timestamp,
                text=f"{layer_label}: {row['reason']} (attempt {row['attempt']})",
            )
        )
    if not events:
        events.append(StoryEvent(timestamp="—", text=f"Story #{story_id} is {story_row['state']}"))
    return events


def _format_event_time(value: str) -> str:
    parsed = parse_timestamp(value)
    if parsed is None:
        return "—"
    return parsed.strftime("%H:%M")


def _worker_display_health(health: str, worker_state: str) -> str:
    if worker_state in {"running", "starting"} and health == "healthy":
        return "healthy"
    if worker_state == "idle" and health == "healthy":
        return "idle"
    if worker_state == "failed" or health == "degraded":
        return "restarting"
    if health == "unresponsive":
        return "restarting"
    return health


def _read_log_excerpt(logs_dir: Path, worker_id: int, *, max_lines: int = 5) -> list[str]:
    log_path = logs_dir / f"worker-{worker_id}.log"
    if not log_path.exists():
        return []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return lines[-max_lines:]


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
