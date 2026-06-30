from __future__ import annotations

import sqlite3
import unittest

from ralph.common.db import apply_schema
from ralph.common.models import StoryState
from ralph.common.protocol import Request, Response
from ralph.pipeline import is_valid_transition


class CommonTests(unittest.TestCase):
    def test_story_states_are_complete(self) -> None:
        self.assertEqual(
            {state.value for state in StoryState},
            {"queued", "in_progress", "in_review", "blocked", "done", "failed"},
        )

    def test_pipeline_transition_contract(self) -> None:
        self.assertTrue(is_valid_transition(StoryState.QUEUED, StoryState.IN_PROGRESS))
        self.assertFalse(is_valid_transition(StoryState.QUEUED, StoryState.DONE))

    def test_protocol_serialization_shape(self) -> None:
        self.assertEqual(Request(type="retry", story_id=7).to_json_dict(), {"type": "retry", "story_id": 7})
        self.assertEqual(Response(type="ok", message="ready").to_json_dict(), {"type": "ok", "message": "ready"})

    def test_schema_creates_expected_tables(self) -> None:
        connection = sqlite3.connect(":memory:")
        apply_schema(connection)
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
        self.assertEqual(
            [row[0] for row in rows],
            ["diagnostic_reports", "healing_attempts", "stories", "story_dependencies", "workers"],
        )


if __name__ == "__main__":
    unittest.main()
