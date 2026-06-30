from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ralph.common.db.store import StateStore
from ralph.common.models import SprintPlan, Story, StoryState
from ralph.pipeline.artifact import (
    iter_story_keys,
    load_sprint_status,
    read_story_artifact,
    require_sprint_status,
    story_key_to_id,
    story_location_dir,
)
from ralph.pipeline.artifact.parser import story_key_from_id
from ralph.pipeline.dependency_graph import DependencyGraph

_SPRINT_STATUS_TO_STORY_STATE = {
    "backlog": StoryState.QUEUED,
    "ready-for-dev": StoryState.QUEUED,
    "in-progress": StoryState.IN_PROGRESS,
    "review": StoryState.IN_REVIEW,
    "done": StoryState.DONE,
    "blocked": StoryState.BLOCKED,
    "failed": StoryState.FAILED,
}


@dataclass(frozen=True, slots=True)
class IngestionResult:
    sprint_plan: SprintPlan
    graph: DependencyGraph
    sprint_status_path: Path
    story_count: int
    dependency_count: int


def ingest_sprint_plan(project_dir: str | Path) -> IngestionResult:
    sprint_status_path = require_sprint_status(project_dir)
    sprint_status = load_sprint_status(sprint_status_path)
    development_status = sprint_status["development_status"]
    assert isinstance(development_status, dict)

    story_dir = story_location_dir(sprint_status, sprint_status_path)
    stories: list[Story] = []
    for story_key in iter_story_keys(development_status):
        sprint_state = str(development_status[story_key]).strip().lower()
        artifact = read_story_artifact(story_dir, story_key)
        story_id = story_key_to_id(story_key)
        dependencies = _resolve_dependencies(story_key, artifact.dependencies, development_status)
        stories.append(
            Story(
                id=story_id,
                key=story_key,
                title=artifact.title,
                state=_map_sprint_status(sprint_state),
                dependencies=dependencies,
                acceptance_criteria=artifact.acceptance_criteria,
            )
        )

    graph = build_dependency_graph(stories)
    graph.validate()

    return IngestionResult(
        sprint_plan=SprintPlan(stories=stories),
        graph=graph,
        sprint_status_path=sprint_status_path,
        story_count=len(stories),
        dependency_count=graph.dependency_count,
    )


def build_dependency_graph(stories: list[Story]) -> DependencyGraph:
    graph = DependencyGraph()
    for story in stories:
        graph.add_story(story)
    return graph


def persist_ingested_plan(store: StateStore, result: IngestionResult) -> None:
    for story in result.sprint_plan.stories:
        store.upsert_story(story)
    store.replace_story_dependencies(
        {story.id: story.dependencies for story in result.sprint_plan.stories}
    )


def _resolve_dependencies(
    story_key: str,
    explicit_dependencies: list[str],
    development_status: dict[str, object],
) -> list[int]:
    if explicit_dependencies:
        return [story_key_to_id(dep) for dep in explicit_dependencies]

    epic, story_num = story_key_from_id(story_key_to_id(story_key))
    if story_num <= 1:
        return []

    previous_key = _find_previous_story_key(epic, story_num - 1, development_status)
    if previous_key is None:
        return []
    return [story_key_to_id(previous_key)]


def _find_previous_story_key(epic: int, story_num: int, development_status: dict[str, object]) -> str | None:
    prefix = f"{epic}-{story_num}-"
    for key in development_status:
        if isinstance(key, str) and key.startswith(prefix):
            return key
    return None


def _map_sprint_status(status: str) -> StoryState:
    return _SPRINT_STATUS_TO_STORY_STATE.get(status, StoryState.QUEUED)
