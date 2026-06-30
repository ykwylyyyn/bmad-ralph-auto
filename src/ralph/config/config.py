from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

DEFAULT_MAX_WORKERS = 5


@dataclass(frozen=True, slots=True)
class RalphConfig:
    max_workers: int | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> "RalphConfig":
        max_workers = data.get("max_workers")
        if max_workers is not None and not isinstance(max_workers, int):
            raise ValueError("max_workers must be an integer")
        if isinstance(max_workers, int) and max_workers < 1:
            raise ValueError("max_workers must be positive")
        return cls(max_workers=max_workers)

    def merge(self, other: "RalphConfig") -> "RalphConfig":
        return RalphConfig(
            max_workers=other.max_workers if other.max_workers is not None else self.max_workers,
        )

    def effective(self) -> "RalphConfig":
        return RalphConfig(max_workers=self.max_workers or DEFAULT_MAX_WORKERS)


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
    return "\n".join(lines) + "\n"
