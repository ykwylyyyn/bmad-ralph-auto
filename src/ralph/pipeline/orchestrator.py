from __future__ import annotations

from ralph.memory.store import MemoryStore
from ralph.pipeline.story_cycle.config import StoryCycleConfig


class StoryCycleOrchestrator:
    """Tracks per-story BMAD-equivalent cycle steps when story_cycle is enabled."""

    def __init__(
        self,
        memory: MemoryStore,
        config: StoryCycleConfig,
    ) -> None:
        self._memory = memory
        self._config = config.effective()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def steps(self) -> tuple[str, ...]:
        return self._config.steps

    def current_step(self, story_id: int) -> str:
        if not self.enabled:
            return "dev"
        index = self._memory.get_step_index(story_id)
        steps = self.steps
        if index >= len(steps):
            return steps[-1]
        return steps[index]

    def complete_step(self, story_id: int, step: str) -> str | None:
        """Record step completion and return the next step name, if any."""

        if not self.enabled:
            return None

        self._memory.add_completed_step(story_id, step)
        index = self._memory.get_step_index(story_id)
        if self.steps[index] != step:
            index = self.steps.index(step) if step in self.steps else index
        next_index = index + 1
        self._memory.set_step_index(story_id, next_index)
        if next_index >= len(self.steps):
            return None
        return self.steps[next_index]

    def has_more_steps(self, story_id: int) -> bool:
        if not self.enabled:
            return False
        return self._memory.get_step_index(story_id) < len(self.steps)

    def is_verify_step(self, step: str) -> bool:
        return step == "verify"

    def is_claude_step(self, step: str) -> bool:
        return step in {"atdd", "dev", "qa"}

    def reset_story(self, story_id: int) -> None:
        self._memory.clear_cycle(story_id)
