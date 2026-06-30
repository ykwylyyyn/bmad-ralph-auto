from __future__ import annotations

from dataclasses import dataclass, field

from ralph.common.models import Story


@dataclass(slots=True)
class DependencyGraph:
    stories: dict[int, Story] = field(default_factory=dict)
    edges: dict[int, list[int]] = field(default_factory=dict)

    def add_story(self, story: Story) -> None:
        self.stories[story.id] = story
        self.edges.setdefault(story.id, list(story.dependencies))

    @property
    def dependency_count(self) -> int:
        return sum(len(deps) for deps in self.edges.values())

    def roots(self) -> list[Story]:
        return [story for story in self.stories.values() if not self.edges.get(story.id)]

    def dependents_of(self, story_id: int) -> list[int]:
        return [sid for sid, deps in self.edges.items() if story_id in deps]

    def schedulable(self, completed: set[int]) -> list[Story]:
        ready: list[Story] = []
        for story in self.stories.values():
            if story.state.value in {"done", "failed"}:
                continue
            deps = self.edges.get(story.id, [])
            if all(dep in completed for dep in deps):
                ready.append(story)
        return sorted(ready, key=lambda item: item.id)

    def validate(self) -> None:
        for story_id, deps in self.edges.items():
            if story_id not in self.stories:
                raise ValueError(f"dependency graph references unknown story {story_id}")
            for dep_id in deps:
                if dep_id not in self.stories:
                    raise ValueError(f"story {story_id} depends on unknown story {dep_id}")
                if dep_id == story_id:
                    raise ValueError(f"story {story_id} cannot depend on itself")

        visiting: set[int] = set()
        visited: set[int] = set()

        def visit(node: int) -> None:
            if node in visiting:
                raise ValueError(f"dependency cycle detected at story {node}")
            if node in visited:
                return
            visiting.add(node)
            for dep in self.edges.get(node, []):
                visit(dep)
            visiting.remove(node)
            visited.add(node)

        for story_id in self.stories:
            visit(story_id)
