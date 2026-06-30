from __future__ import annotations

from dataclasses import dataclass
import re

import yaml

from .errors import ArtifactParseError

_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_STORY_HEADING_PATTERN = re.compile(r"^#\s+Story\s+(\d+)\.(\d+):\s*(.+?)\s*$", re.MULTILINE)
_STATUS_PATTERN = re.compile(r"^Status:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
_ACCEPTANCE_SECTION_PATTERN = re.compile(
    r"^##\s+Acceptance Criteria\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_NEXT_SECTION_PATTERN = re.compile(r"^##\s+", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ParsedArtifact:
    frontmatter: dict[str, object]
    body: str


@dataclass(frozen=True, slots=True)
class ParsedStoryArtifact:
    key: str
    title: str
    status: str
    acceptance_criteria: list[str]
    dependencies: list[str]
    body: str


def parse_frontmatter(content: str, *, source: str = "<memory>") -> ParsedArtifact:
    text = content.lstrip("\ufeff")
    if not text.startswith("---"):
        return ParsedArtifact(frontmatter={}, body=text)

    match = _FRONTMATTER_PATTERN.match(text)
    if match is None:
        raise ArtifactParseError(source, "YAML frontmatter is not terminated with ---")

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ArtifactParseError(source, f"invalid YAML frontmatter: {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise ArtifactParseError(source, "YAML frontmatter must be a mapping")

    return ParsedArtifact(frontmatter=frontmatter, body=match.group(2))


def parse_story_markdown(content: str, *, story_key: str, source: str) -> ParsedStoryArtifact:
    artifact = parse_frontmatter(content, source=source)
    body = artifact.body

    title = _title_from_frontmatter(artifact.frontmatter)
    if title is None:
        title = _title_from_heading(body)
    if title is None:
        title = _title_from_key(story_key)

    status = _status_from_frontmatter(artifact.frontmatter)
    if status is None:
        status = _status_from_body(body)

    acceptance_criteria = _acceptance_from_frontmatter(artifact.frontmatter)
    if not acceptance_criteria:
        acceptance_criteria = _acceptance_from_body(body)

    dependencies = _dependencies_from_frontmatter(artifact.frontmatter)

    return ParsedStoryArtifact(
        key=story_key,
        title=title,
        status=status,
        acceptance_criteria=acceptance_criteria,
        dependencies=dependencies,
        body=body,
    )


def story_key_to_id(story_key: str) -> int:
    match = re.match(r"^(\d+)-(\d+)-", story_key)
    if match is None:
        raise ValueError(f"invalid story key: {story_key}")
    epic = int(match.group(1))
    story = int(match.group(2))
    return epic * 1000 + story


def story_key_from_id(story_id: int) -> tuple[int, int]:
    epic = story_id // 1000
    story = story_id % 1000
    return epic, story


def _title_from_frontmatter(frontmatter: dict[str, object]) -> str | None:
    for field in ("title", "story_title", "name"):
        value = frontmatter.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _title_from_heading(body: str) -> str | None:
    match = _STORY_HEADING_PATTERN.search(body)
    if match is None:
        return None
    return match.group(3).strip()


def _title_from_key(story_key: str) -> str:
    slug = story_key.split("-", 2)[-1]
    return slug.replace("-", " ").strip()


def _status_from_frontmatter(frontmatter: dict[str, object]) -> str | None:
    value = frontmatter.get("status")
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return None


def _status_from_body(body: str) -> str:
    match = _STATUS_PATTERN.search(body)
    if match is None:
        return "backlog"
    return match.group(1).strip().lower()


def _acceptance_from_frontmatter(frontmatter: dict[str, object]) -> list[str]:
    value = frontmatter.get("acceptance_criteria")
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _acceptance_from_body(body: str) -> list[str]:
    section_match = _ACCEPTANCE_SECTION_PATTERN.search(body)
    if section_match is None:
        return []

    start = section_match.end()
    remainder = body[start:]
    next_section = _NEXT_SECTION_PATTERN.search(remainder)
    section_text = remainder[: next_section.start()] if next_section else remainder

    criteria: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0].isdigit() and "." in stripped[:4]:
            criteria.append(stripped)
        elif stripped.startswith("**") and stripped.endswith("**"):
            criteria.append(stripped.strip("*"))
    return criteria


def _dependencies_from_frontmatter(frontmatter: dict[str, object]) -> list[str]:
    value = frontmatter.get("dependencies")
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
