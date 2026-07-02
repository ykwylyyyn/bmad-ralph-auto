from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
  enabled: bool = False
  feedback_loop: bool = False
  auto_done: bool = False

  @classmethod
  def from_mapping(cls, data: object) -> OrchestratorConfig:
    if not isinstance(data, dict):
      raise ValueError("orchestrator must be a table")

    enabled = data.get("enabled", False)
    if not isinstance(enabled, bool):
      raise ValueError("orchestrator.enabled must be a boolean")

    feedback_loop = data.get("feedback_loop", False)
    if not isinstance(feedback_loop, bool):
      raise ValueError("orchestrator.feedback_loop must be a boolean")

    auto_done = data.get("auto_done", False)
    if not isinstance(auto_done, bool):
      raise ValueError("orchestrator.auto_done must be a boolean")

    return cls(enabled=enabled, feedback_loop=feedback_loop, auto_done=auto_done)

  def effective(self) -> OrchestratorConfig:
    if not self.enabled:
      return OrchestratorConfig(enabled=False)
    return OrchestratorConfig(
      enabled=True,
      feedback_loop=self.feedback_loop,
      auto_done=self.auto_done,
    )
