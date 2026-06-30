from __future__ import annotations

from pathlib import Path
import re

import yaml

from .errors import ArtifactParseError, SprintPlanNotFoundError
from .parser import ParsedStoryArtifact, parse_story_markdown

DEFAULT_ARTIFACTS_DIR = Path("_bmad-output") / "implementation-artifacts"
SPRINT_STATUS_FILE = "sprint-status.yaml"
STORY_KEY_PATTERN = re.compile(r"^\d+-\d+-.+$")


def default_sprint_status_path(project_dir: str | Path) -> Path:
    return Path(project_dir).resolve() / DEFAULT_ARTIFACTS_DIR / SPRINT_STATUS_FILE


def find_sprint_status(project_dir: str | Path) -> Path | None:
    path = default_sprint_status_path(project_dir)
    return path if path.is_file() else None


def require_sprint_status(project_dir: str | Path) -> Path:
    path = find_sprint_status(project_dir)
    if path is None:
        raise SprintPlanNotFoundError(str(Path(project_dir).resolve()))
    return path


def load_sprint_status(path: str | Path) -> dict[str, object]:
    source = str(path)
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactParseError(source, str(exc)) from exc

    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        raise ArtifactParseError(source, f"invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ArtifactParseError(source, "sprint status root must be a mapping")

    development_status = data.get("development_status")
    if not isinstance(development_status, dict) or not development_status:
        raise ArtifactParseError(source, "development_status missing or empty")

    return data


def story_location_dir(sprint_status: dict[str, object], sprint_status_path: Path) -> Path:
    project_dir = project_dir_from_sprint_status(sprint_status_path)
    raw = sprint_status.get("story_location")
    if isinstance(raw, str) and raw.strip():
        location = Path(raw.strip())
        if location.is_absolute():
            return location
        return project_dir / location
    return sprint_status_path.parent


def project_dir_from_sprint_status(sprint_status_path: Path) -> Path:
    if (
        sprint_status_path.parent.name == "implementation-artifacts"
        and sprint_status_path.parent.parent.name == "_bmad-output"
    ):
        return sprint_status_path.parent.parent.parent
    return sprint_status_path.parent


def iter_story_keys(development_status: dict[str, object]) -> list[str]:
    keys: list[str] = []
    for key, value in development_status.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if key.startswith("epic-"):
            continue
        if STORY_KEY_PATTERN.match(key):
            keys.append(key)
    return keys


def read_story_artifact(story_dir: Path, story_key: str) -> ParsedStoryArtifact:
    path = story_dir / f"{story_key}.md"
    if not path.is_file():
        return ParsedStoryArtifact(
            key=story_key,
            title=story_key.split("-", 2)[-1].replace("-", " "),
            status="backlog",
            acceptance_criteria=[],
            dependencies=[],
            body="",
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactParseError(str(path), str(exc)) from exc

    return parse_story_markdown(content, story_key=story_key, source=str(path))
