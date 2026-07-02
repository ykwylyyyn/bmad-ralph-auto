from __future__ import annotations

from dataclasses import dataclass

VALID_CYCLE_STEPS = frozenset({"atdd", "dev", "verify", "qa"})
DEFAULT_CYCLE_STEPS = ("dev",)
DEFAULT_ARTIFACTS_DIR = "_bmad-output"
DEFAULT_PROMPT_MAX_CHARS = 32_000


@dataclass(frozen=True, slots=True)
class StoryCycleConfig:
    enabled: bool = False
    steps: tuple[str, ...] = DEFAULT_CYCLE_STEPS
    max_step_retries: int = 3
    artifacts_dir: str = DEFAULT_ARTIFACTS_DIR
    prompt_max_chars: int = DEFAULT_PROMPT_MAX_CHARS

    @classmethod
    def from_mapping(cls, data: object) -> "StoryCycleConfig":
        if not isinstance(data, dict):
            raise ValueError("story_cycle must be a table")

        enabled = data.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("story_cycle.enabled must be a boolean")

        max_step_retries = data.get("max_step_retries", 3)
        if not isinstance(max_step_retries, int) or max_step_retries < 1:
            raise ValueError("story_cycle.max_step_retries must be a positive integer")

        artifacts_dir = data.get("artifacts_dir", DEFAULT_ARTIFACTS_DIR)
        if not isinstance(artifacts_dir, str) or not artifacts_dir.strip():
            raise ValueError("story_cycle.artifacts_dir must be a non-empty string")

        prompt_max_chars = data.get("prompt_max_chars", DEFAULT_PROMPT_MAX_CHARS)
        if not isinstance(prompt_max_chars, int) or prompt_max_chars < 1_000:
            raise ValueError("story_cycle.prompt_max_chars must be an integer >= 1000")

        raw_steps = data.get("steps", list(DEFAULT_CYCLE_STEPS))
        if raw_steps is None:
            raw_steps = list(DEFAULT_CYCLE_STEPS)
        if not isinstance(raw_steps, list) or not all(isinstance(item, str) for item in raw_steps):
            raise ValueError("story_cycle.steps must be a list of strings")

        steps = tuple(item.strip().lower() for item in raw_steps if item.strip())
        invalid = [step for step in steps if step not in VALID_CYCLE_STEPS]
        if invalid:
            raise ValueError(f"story_cycle.steps contains invalid steps: {', '.join(invalid)}")

        return cls(
            enabled=enabled,
            steps=steps or DEFAULT_CYCLE_STEPS,
            max_step_retries=max_step_retries,
            artifacts_dir=artifacts_dir.strip(),
            prompt_max_chars=prompt_max_chars,
        )

    def effective(self) -> "StoryCycleConfig":
        if not self.enabled:
            return StoryCycleConfig(enabled=False)
        return StoryCycleConfig(
            enabled=True,
            steps=self.steps or DEFAULT_CYCLE_STEPS,
            max_step_retries=self.max_step_retries,
            artifacts_dir=self.artifacts_dir,
            prompt_max_chars=self.prompt_max_chars,
        )
