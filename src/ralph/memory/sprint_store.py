from __future__ import annotations

from typing import Any

from ralph.common.db.store import StateStore

SPRINT_SNAPSHOT_KEY = "sprint.snapshot"
SPRINT_MODULES_KEY = "sprint.completed_modules"
SPRINT_APIS_KEY = "sprint.completed_apis"
SPRINT_FAILURE_PATTERNS_KEY = "sprint.failure_patterns"


class SprintMemoryStore:
  """Sprint-scoped memory shared across stories (cross-story execution context)."""

  def __init__(self, store: StateStore) -> None:
    self._store = store

  def get(self, key: str) -> Any | None:
    return self._store.get_sprint_memory(key)

  def set(self, key: str, value: object) -> None:
    self._store.set_sprint_memory(key, value)

  def record_snapshot(self, snapshot: dict[str, object]) -> None:
    self.set(SPRINT_SNAPSHOT_KEY, snapshot)

  def get_snapshot(self) -> dict[str, object]:
    value = self.get(SPRINT_SNAPSHOT_KEY)
    return dict(value) if isinstance(value, dict) else {}

  def add_completed_module(self, module: str) -> None:
    modules = self.get(SPRINT_MODULES_KEY)
    if not isinstance(modules, list):
      modules = []
    if module not in modules:
      modules.append(module)
    self.set(SPRINT_MODULES_KEY, modules)

  def get_completed_modules(self) -> list[str]:
    value = self.get(SPRINT_MODULES_KEY)
    if not isinstance(value, list):
      return []
    return [str(item) for item in value]

  def add_completed_api(self, api: str) -> None:
    apis = self.get(SPRINT_APIS_KEY)
    if not isinstance(apis, list):
      apis = []
    if api not in apis:
      apis.append(api)
    self.set(SPRINT_APIS_KEY, apis)

  def get_completed_apis(self) -> list[str]:
    value = self.get(SPRINT_APIS_KEY)
    if not isinstance(value, list):
      return []
    return [str(item) for item in value]

  def record_failure_pattern(self, category: str, reason: str) -> None:
    patterns = self.get(SPRINT_FAILURE_PATTERNS_KEY)
    if not isinstance(patterns, list):
      patterns = []
    patterns.append({"category": category, "reason": reason})
    self.set(SPRINT_FAILURE_PATTERNS_KEY, patterns[-50:])

  def get_failure_patterns(self) -> list[dict[str, str]]:
    value = self.get(SPRINT_FAILURE_PATTERNS_KEY)
    if not isinstance(value, list):
      return []
    return [
      {"category": str(item.get("category", "")), "reason": str(item.get("reason", ""))}
      for item in value
      if isinstance(item, dict)
    ]

  def build_context_summary(self) -> str:
    modules = self.get_completed_modules()
    apis = self.get_completed_apis()
    patterns = self.get_failure_patterns()
    lines: list[str] = []
    if modules:
      lines.append(f"Completed modules: {', '.join(modules)}")
    if apis:
      lines.append(f"Completed APIs: {', '.join(apis)}")
    if patterns:
      recent = patterns[-3:]
      lines.append(
        "Recent failure patterns: "
        + "; ".join(f"{p['category']}: {p['reason'][:80]}" for p in recent)
      )
    return "\n".join(lines)
