from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import RalphConfig, render_config
from .planning import BmadIntegrationResult, integrate_bmad
from .planning.bmad import ensure_planning_output_dirs


@dataclass(frozen=True, slots=True)
class InitResult:
    project_dir: Path
    config_path: Path
    runtime_dir: Path
    created_config: bool
    bmad: BmadIntegrationResult | None = None


def init_project(
    project_dir: str | Path,
    *,
    max_workers: int = 5,
    force: bool = False,
    integrate_bmad_submodule: bool = True,
) -> InitResult:
    root = Path(project_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    config_path = root / "ralph.toml"
    runtime_dir = root / ".ralph"
    runtime_dir.mkdir(exist_ok=True)
    (runtime_dir / "logs").mkdir(exist_ok=True)
    (runtime_dir / "worktrees").mkdir(exist_ok=True)

    created_config = False
    if force or not config_path.exists():
        config_path.write_text(render_config(RalphConfig(max_workers=max_workers)), encoding="utf-8")
        created_config = True

    ensure_planning_output_dirs(root)
    bmad_result = integrate_bmad(root) if integrate_bmad_submodule else None

    return InitResult(
        project_dir=root,
        config_path=config_path,
        runtime_dir=runtime_dir,
        created_config=created_config,
        bmad=bmad_result,
    )
