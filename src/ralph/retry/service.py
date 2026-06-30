from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ralph.common.db.errors import StoryNotFoundError
from ralph.common.db.store import StateStore
from ralph.common.models import Story, StoryState
from ralph.daemon import RuntimePaths, read_status

_STATE_DISPLAY = {
    StoryState.QUEUED: "queued",
    StoryState.IN_PROGRESS: "running",
    StoryState.IN_REVIEW: "running",
    StoryState.BLOCKED: "blocked",
    StoryState.DONE: "completed",
    StoryState.FAILED: "failed",
}


class RetryErrorKind(StrEnum):
    NO_DAEMON = "no_daemon"
    STORY_NOT_FOUND = "story_not_found"
    INVALID_STATE = "invalid_state"


@dataclass(frozen=True, slots=True)
class RetryError:
    kind: RetryErrorKind
    story_id: int | None = None
    state_label: str | None = None


@dataclass(frozen=True, slots=True)
class RetryResult:
    story_id: int
    title: str
    worker_assignment: str


def retry_story(project_dir: str | Path, story_id: int) -> RetryResult | RetryError:
    paths = RuntimePaths(Path(project_dir).resolve())
    daemon = read_status(paths.project_dir)
    if daemon.state != "running" or (daemon.pid is not None and not _pid_exists(daemon.pid)):
        return RetryError(kind=RetryErrorKind.NO_DAEMON, story_id=story_id)

    if not paths.database_file.exists():
        return RetryError(kind=RetryErrorKind.STORY_NOT_FOUND, story_id=story_id)

    store = StateStore.open(paths.database_file)
    try:
        try:
            story = store.get_story(story_id)
        except StoryNotFoundError:
            return RetryError(kind=RetryErrorKind.STORY_NOT_FOUND, story_id=story_id)

        if story.state != StoryState.FAILED:
            return RetryError(
                kind=RetryErrorKind.INVALID_STATE,
                story_id=story_id,
                state_label=_STATE_DISPLAY.get(story.state, story.state.value),
            )

        store.reset_healing_state(story_id)
        updated = store.get_story(story_id)
        return RetryResult(
            story_id=updated.id,
            title=updated.title,
            worker_assignment="pending assignment",
        )
    finally:
        store.close()


def _pid_exists(pid: int) -> bool:
    import os

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
