from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from ralph.common.db import StateStore
from ralph.common.models import Story, StoryState
from ralph.pipeline.ingestion import ingest_sprint_plan, persist_ingested_plan
from ralph.pipeline.artifact import ArtifactParseError, SprintPlanNotFoundError
from ralph.pipeline.dependency_graph import DependencyGraph


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.artifacts = self.root / "_bmad-output" / "implementation-artifacts"
        self.artifacts.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_sprint_status(self, body: str) -> None:
        (self.artifacts / "sprint-status.yaml").write_text(body, encoding="utf-8")

    def _write_story(self, key: str, content: str) -> None:
        (self.artifacts / f"{key}.md").write_text(content, encoding="utf-8")

    def test_ingest_project_sprint_plan(self) -> None:
        self._write_sprint_status(
            textwrap.dedent(
                """\
                generated: 2026-02-28
                project: demo
                story_location: _bmad-output/implementation-artifacts

                development_status:
                  epic-1: in-progress
                  1-1-first-story: backlog
                  1-2-second-story: backlog
                  epic-1-retrospective: optional
                """
            )
        )
        self._write_story(
            "1-1-first-story",
            "# Story 1.1: First Story\n\n## Acceptance Criteria\n\n1. **AC1:** first",
        )
        self._write_story(
            "1-2-second-story",
            textwrap.dedent(
                """\
                ---
                dependencies:
                  - 1-1-first-story
                ---
                # Story 1.2: Second Story

                ## Acceptance Criteria

                1. **AC1:** second
                """
            ),
        )

        result = ingest_sprint_plan(self.root)
        self.assertEqual(result.story_count, 2)
        self.assertEqual(result.dependency_count, 1)
        self.assertEqual(result.sprint_plan.stories[0].id, 1001)
        self.assertEqual(result.sprint_plan.stories[1].dependencies, [1001])
        self.assertEqual(len(result.sprint_plan.stories[1].acceptance_criteria), 1)

    def test_dependency_graph_detects_cycles(self) -> None:
        graph = DependencyGraph()
        graph.add_story(_story(1001, [1002]))
        graph.add_story(_story(1002, [1001]))
        with self.assertRaises(ValueError):
            graph.validate()

    def test_missing_sprint_plan_error(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(SprintPlanNotFoundError):
            ingest_sprint_plan(empty)

    def test_malformed_sprint_status_reports_file(self) -> None:
        self._write_sprint_status("not: [valid")
        with self.assertRaises(ArtifactParseError) as ctx:
            ingest_sprint_plan(self.root)
        self.assertIn("sprint-status.yaml", ctx.exception.path)

    def test_persist_ingested_plan_writes_dependencies(self) -> None:
        self._write_sprint_status(
            textwrap.dedent(
                """\
                story_location: _bmad-output/implementation-artifacts
                development_status:
                  2-1-alpha: backlog
                  2-2-beta: backlog
                """
            )
        )
        self._write_story("2-1-alpha", "# Story 2.1: Alpha")
        self._write_story("2-2-beta", "# Story 2.2: Beta")

        result = ingest_sprint_plan(self.root)
        store = StateStore.open_in_memory()
        try:
            persist_ingested_plan(store, result)
            stories = store.list_stories()
            self.assertEqual(len(stories), 2)
            deps = store.list_story_dependencies()
            self.assertEqual(deps.get(2002), [2001])
        finally:
            store.close()

    def test_start_without_sprint_plan_exits_with_guidance(self) -> None:
        from ralph.cli import main
        from io import StringIO
        import contextlib

        empty = self.root / "no-plan"
        empty.mkdir()
        stdout = StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as ctx:
                main(["start", "--project-dir", str(empty)])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No sprint plan found in project", stdout.getvalue())

    def test_ingest_real_repo_sprint_plan(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        if not (repo_root / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml").exists():
            self.skipTest("repository sprint plan not available")

        result = ingest_sprint_plan(repo_root)
        self.assertGreater(result.story_count, 10)
        self.assertGreaterEqual(result.dependency_count, 1)
        result.graph.validate()


def _story(story_id: int, dependencies: list[int]) -> Story:
    return Story(id=story_id, title=f"Story {story_id}", dependencies=dependencies)


if __name__ == "__main__":
    unittest.main()
