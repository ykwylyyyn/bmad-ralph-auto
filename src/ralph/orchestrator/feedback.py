from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
  artifact_path: str
  event_type: str
  story_key: str | None = None


class BmadFeedbackWatcher:
  """Watches _bmad-output for review/CR artifacts that may trigger re-plan or retry."""

  _WATCH_SUFFIXES = (".md", ".yaml", ".yml")
  _REVIEW_MARKERS = ("code-review", "cr-", "review", "qa-", "tr-")

  def __init__(self, project_dir: Path, artifacts_dir: str = "_bmad-output") -> None:
    self._root = (project_dir / artifacts_dir).resolve()
    self._seen: set[str] = set()

  def poll(self) -> list[FeedbackEvent]:
    if not self._root.exists():
      return []

    events: list[FeedbackEvent] = []
    for path in sorted(self._root.rglob("*")):
      if not path.is_file():
        continue
      if path.suffix.lower() not in self._WATCH_SUFFIXES:
        continue
      key = str(path)
      if key in self._seen:
        continue
      self._seen.add(key)
      lowered = path.name.lower()
      if not any(marker in lowered for marker in self._REVIEW_MARKERS):
        continue
      story_key = _extract_story_key(path.name)
      events.append(
        FeedbackEvent(
          artifact_path=key,
          event_type="review_artifact_detected",
          story_key=story_key,
        )
      )
    return events


def _extract_story_key(filename: str) -> str | None:
  stem = filename.rsplit(".", 1)[0]
  for part in stem.split("-"):
    if part.isdigit():
      continue
    if len(part) >= 2:
      return stem
  return None
