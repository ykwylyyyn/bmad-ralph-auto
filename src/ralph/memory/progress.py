from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from ralph.pipeline.artifact.reader import (
    DEFAULT_ARTIFACTS_DIR,
    find_sprint_status,
    load_sprint_status,
)

STEP_SPRINT_STATUS: dict[str, str] = {
    "atdd": "in-progress",
    "dev": "in-progress",
    "verify": "review",
    "qa": "review",
}

CYCLE_COMPLETE_STATUS = "review"


def sync_story_progress(
    project_dir: Path,
    story_key: str,
    step: str,
    *,
    artifacts_dir: str | Path = DEFAULT_ARTIFACTS_DIR,
    cycle_complete: bool = False,
    write_progress_md: bool = True,
) -> bool:
    """Update sprint-status.yaml and optional BMAD-compatible progress artifact."""

    root = project_dir.resolve()
    sprint_status_path = find_sprint_status(root)
    if sprint_status_path is None:
        return False

    try:
        data = load_sprint_status(sprint_status_path)
    except Exception:
        return False

    development_status = data.get("development_status")
    if not isinstance(development_status, dict):
        return False
    if story_key not in development_status:
        return False

    status = CYCLE_COMPLETE_STATUS if cycle_complete else STEP_SPRINT_STATUS.get(step, "in-progress")
    development_status[story_key] = status

    try:
        sprint_status_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except OSError:
        return False

    if write_progress_md:
        _write_progress_markdown(
            root,
            story_key=story_key,
            step=step,
            status=status,
            artifacts_dir=Path(artifacts_dir),
        )
    return True


def _write_progress_markdown(
    project_dir: Path,
    *,
    story_key: str,
    step: str,
    status: str,
    artifacts_dir: Path,
) -> None:
    progress_dir = project_dir / artifacts_dir / "test-artifacts"
    progress_dir.mkdir(parents=True, exist_ok=True)
    progress_path = progress_dir / f"story-{story_key}-progress.md"
    timestamp = datetime.now(timezone.utc).isoformat()
    content = (
        "---\n"
        f"story_key: {story_key}\n"
        f"last_step: {step}\n"
        f"status: {status}\n"
        f"updated_at: {timestamp}\n"
        "---\n\n"
        f"# Story {story_key} progress\n\n"
        f"- Last completed step: `{step}`\n"
        f"- Sprint status: `{status}`\n"
    )
    try:
        progress_path.write_text(content, encoding="utf-8")
    except OSError:
        return
