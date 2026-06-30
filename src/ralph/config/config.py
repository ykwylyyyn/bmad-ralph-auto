from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True, slots=True)
class RalphConfig:
    max_workers: int | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, object]) -> "RalphConfig":
        max_workers = data.get("max_workers")
        if max_workers is not None and not isinstance(max_workers, int):
            raise ValueError("max_workers must be an integer")
        return cls(max_workers=max_workers)


def load_config(path: str | Path) -> RalphConfig:
    content = Path(path).read_bytes()
    return RalphConfig.from_mapping(tomllib.loads(content.decode("utf-8")))
