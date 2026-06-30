from __future__ import annotations

import textwrap
import unittest

from ralph.pipeline.artifact import (
    ArtifactParseError,
    SprintPlanNotFoundError,
    load_sprint_status,
    parse_frontmatter,
    parse_story_markdown,
    story_key_to_id,
)


class ArtifactParserTests(unittest.TestCase):
    def test_parse_frontmatter_deserializes_yaml_and_keeps_body(self) -> None:
        content = textwrap.dedent(
            """\
            ---
            status: ready-for-dev
            dependencies:
              - 1-1-user-auth
            ---
            # Story body
            Details here.
            """
        )
        artifact = parse_frontmatter(content)
        self.assertEqual(artifact.frontmatter["status"], "ready-for-dev")
        self.assertEqual(artifact.frontmatter["dependencies"], ["1-1-user-auth"])
        self.assertIn("# Story body", artifact.body)

    def test_parse_story_markdown_without_frontmatter(self) -> None:
        content = textwrap.dedent(
            """\
            # Story 2.4: BMAD Artifact Parsing

            Status: backlog

            ## Acceptance Criteria

            1. **AC1:** Given a sprint plan, when ingested, then stories are identified.
            """
        )
        parsed = parse_story_markdown(content, story_key="2-4-bmad-artifact-parsing", source="story.md")
        self.assertEqual(parsed.title, "BMAD Artifact Parsing")
        self.assertEqual(parsed.status, "backlog")
        self.assertEqual(len(parsed.acceptance_criteria), 1)

    def test_parse_story_markdown_rejects_invalid_frontmatter(self) -> None:
        content = "---\n: invalid\n---\nbody"
        with self.assertRaises(ArtifactParseError):
            parse_frontmatter(content, source="broken.md")

    def test_story_key_to_id(self) -> None:
        self.assertEqual(story_key_to_id("2-4-bmad-artifact-parsing"), 2004)


class SprintStatusReaderTests(unittest.TestCase):
    def test_load_sprint_status_requires_development_status(self) -> None:
        with self.assertRaises(ArtifactParseError):
            load_sprint_status_from_text("project: demo\n")

    def test_missing_sprint_plan_raises(self) -> None:
        with self.assertRaises(SprintPlanNotFoundError):
            from ralph.pipeline.artifact import require_sprint_status

            require_sprint_status("/tmp/does-not-exist-ralph-project")


def load_sprint_status_from_text(content: str) -> dict[str, object]:
    from pathlib import Path
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        handle.write(content)
        path = Path(handle.name)
    try:
        return load_sprint_status(path)
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
