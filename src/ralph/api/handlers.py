from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from ralph.common.db.errors import StoryNotFoundError
from ralph.common.db.store import StateStore
from ralph.common.models import StoryState


@dataclass(frozen=True, slots=True)
class ApiResponse:
  status: int
  body: dict[str, Any]

  def to_bytes(self) -> bytes:
    return json.dumps(self.body, indent=2, sort_keys=True).encode("utf-8")


class ApiHandlers:
  """REST handlers backed by SQLite state store."""

  def __init__(self, store: StateStore, project_dir: str) -> None:
    self._store = store
    self._project_dir = project_dir

  def handle(self, method: str, path: str) -> ApiResponse:
    normalized = path.rstrip("/") or "/"
    if method == "GET" and normalized == "/status":
      return self._status()
    if method == "GET" and normalized == "/stories":
      return self._stories()
    if method == "GET" and normalized == "/events":
      return self._events()
    if method == "POST" and normalized.startswith("/retry/"):
      story_id = _parse_id(normalized, "/retry/")
      if story_id is None:
        return ApiResponse(400, {"error": "invalid story id"})
      return self._retry(story_id)
    if method == "POST" and normalized == "/run":
      return ApiResponse(202, {"message": "pipeline runs via daemon tick loop"})
    return ApiResponse(404, {"error": "not found", "path": normalized})

  def _status(self) -> ApiResponse:
    stories = self._store.list_stories()
    workers = self._store.list_workers()
    pipeline_state = self._store.get_pipeline_state()
    return ApiResponse(
      200,
      {
        "project_dir": self._project_dir,
        "pipeline_state": pipeline_state.value,
        "stories": {
          "total": len(stories),
          "done": sum(1 for s in stories if s.state == StoryState.DONE),
          "failed": sum(1 for s in stories if s.state == StoryState.FAILED),
          "active": sum(
            1
            for s in stories
            if s.state
            in {
              StoryState.IN_PROGRESS,
              StoryState.VERIFYING,
              StoryState.IN_REVIEW,
            }
          ),
        },
        "workers": {
          "total": len(workers),
          "running": sum(1 for w in workers if w.state.value == "running"),
        },
      },
    )

  def _stories(self) -> ApiResponse:
    stories = self._store.list_stories()
    return ApiResponse(
      200,
      {
        "stories": [
          {
            "id": story.id,
            "key": story.key,
            "title": story.title,
            "state": story.state.value,
            "worker_id": story.worker_id,
            "dependencies": story.dependencies,
          }
          for story in stories
        ]
      },
    )

  def _events(self) -> ApiResponse:
    events = self._store.list_pipeline_events()
    return ApiResponse(200, {"events": events[-100:]})

  def _retry(self, story_id: int) -> ApiResponse:
    try:
      story = self._store.get_story(story_id)
    except StoryNotFoundError:
      return ApiResponse(404, {"error": "story not found", "story_id": story_id})
    if story.state != StoryState.FAILED:
      return ApiResponse(
        400,
        {"error": "story is not in failed state", "story_id": story_id, "state": story.state.value},
      )
    self._store.reset_healing_state(story_id)
    return ApiResponse(200, {"message": "story re-queued", "story_id": story_id})


def _parse_id(path: str, prefix: str) -> int | None:
  suffix = path[len(prefix) :]
  try:
    return int(suffix)
  except ValueError:
    return None
