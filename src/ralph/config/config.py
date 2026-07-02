from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from ralph.verifier.config import VerifierConfig
from ralph.pipeline.story_cycle import StoryCycleConfig
from ralph.router.config import RouterConfig

DEFAULT_MAX_WORKERS = 5
DEFAULT_RETRY_LIMIT = 3


@dataclass(frozen=True, slots=True)
class RalphConfig:
    max_workers: int | None = None
    retry_limit: int | None = None
    verifier: VerifierConfig | None = None
    story_cycle: StoryCycleConfig | None = None
    router: RouterConfig | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> "RalphConfig":
        max_workers = data.get("max_workers")
        if max_workers is not None and not isinstance(max_workers, int):
            raise ValueError("max_workers must be an integer")
        if isinstance(max_workers, int) and max_workers < 1:
            raise ValueError("max_workers must be positive")

        retry_limit = data.get("retry_limit")
        if retry_limit is not None and not isinstance(retry_limit, int):
            raise ValueError("retry_limit must be an integer")
        if isinstance(retry_limit, int) and retry_limit < 1:
            raise ValueError("retry_limit must be positive")

        verifier = None
        raw_verifier = data.get("verifier")
        if raw_verifier is not None:
            verifier = VerifierConfig.from_mapping(raw_verifier)

        story_cycle = None
        raw_story_cycle = data.get("story_cycle")
        if raw_story_cycle is not None:
            story_cycle = StoryCycleConfig.from_mapping(raw_story_cycle)

        router = None
        raw_router = data.get("router")
        if raw_router is not None:
            router = RouterConfig.from_mapping(raw_router)

        return cls(
            max_workers=max_workers,
            retry_limit=retry_limit,
            verifier=verifier,
            story_cycle=story_cycle,
            router=router,
        )

    def merge(self, other: "RalphConfig") -> "RalphConfig":
        return RalphConfig(
            max_workers=other.max_workers if other.max_workers is not None else self.max_workers,
            retry_limit=other.retry_limit if other.retry_limit is not None else self.retry_limit,
            verifier=other.verifier if other.verifier is not None else self.verifier,
            story_cycle=other.story_cycle if other.story_cycle is not None else self.story_cycle,
            router=other.router if other.router is not None else self.router,
        )

    def effective(self) -> "RalphConfig":
        verifier = self.verifier or VerifierConfig()
        story_cycle = self.story_cycle or StoryCycleConfig()
        router = self.router or RouterConfig()
        return RalphConfig(
            max_workers=self.max_workers or DEFAULT_MAX_WORKERS,
            retry_limit=self.retry_limit or DEFAULT_RETRY_LIMIT,
            verifier=verifier.effective(),
            story_cycle=story_cycle.effective(),
            router=router.effective(),
        )


def load_config(path: str | Path) -> RalphConfig:
    content = Path(path).read_bytes()
    return RalphConfig.from_mapping(tomllib.loads(content.decode("utf-8")))


def load_config_if_exists(path: str | Path | None) -> RalphConfig:
    if path is None:
        return RalphConfig()
    config_path = Path(path)
    if not config_path.exists():
        return RalphConfig()
    return load_config(config_path)


def default_user_config_path(home: str | Path | None = None) -> Path:
    root = Path(home) if home is not None else Path.home()
    return root / ".config" / "ralph" / "ralph.toml"


def default_project_config_path(project_dir: str | Path | None = None) -> Path:
    root = Path(project_dir) if project_dir is not None else Path.cwd()
    return root / "ralph.toml"


def resolve_config(
    *,
    user_config_path: str | Path | None = None,
    project_config_path: str | Path | None = None,
    overrides: RalphConfig | None = None,
) -> RalphConfig:
    config = RalphConfig()
    config = config.merge(load_config_if_exists(user_config_path))
    config = config.merge(load_config_if_exists(project_config_path))
    if overrides is not None:
        config = config.merge(overrides)
    return config.effective()


def render_config(config: RalphConfig) -> str:
    lines = []
    if config.max_workers is not None:
        lines.append(f"max_workers = {config.max_workers}")
    if config.retry_limit is not None:
        lines.append(f"retry_limit = {config.retry_limit}")
    if config.verifier is not None and config.verifier.enabled:
        lines.append("")
        lines.append("[verifier]")
        lines.append(f"enabled = {'true' if config.verifier.enabled else 'false'}")
        if config.verifier.timeout_secs != VerifierConfig().timeout_secs:
            lines.append(f"timeout_secs = {config.verifier.timeout_secs}")
        if config.verifier.commands:
            lines.append("commands = [")
            for command in config.verifier.commands:
                escaped = command.replace('"', '\\"')
                lines.append(f'  "{escaped}",')
            lines.append("]")
    if config.story_cycle is not None and config.story_cycle.enabled:
        lines.append("")
        lines.append("[story_cycle]")
        lines.append("enabled = true")
        if config.story_cycle.max_step_retries != 3:
            lines.append(f"max_step_retries = {config.story_cycle.max_step_retries}")
        if config.story_cycle.artifacts_dir != StoryCycleConfig().artifacts_dir:
            lines.append(f'artifacts_dir = "{config.story_cycle.artifacts_dir}"')
        if config.story_cycle.prompt_max_chars != StoryCycleConfig().prompt_max_chars:
            lines.append(f"prompt_max_chars = {config.story_cycle.prompt_max_chars}")
        lines.append("steps = [")
        for step in config.story_cycle.steps:
            lines.append(f'  "{step}",')
        lines.append("]")
    return "\n".join(lines) + ("\n" if lines else "")
