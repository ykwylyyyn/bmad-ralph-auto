from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ralph.memory.skill_loader import find_skill_dir, load_skill_excerpt
from ralph.pipeline.story_cycle.config import StoryCycleConfig
from ralph.pipeline.orchestrator import StoryCycleOrchestrator
from ralph.common.db.store import StateStore
from ralph.common.models import Story
from ralph.memory.store import MemoryStore


class StoryCycleConfigTests(unittest.TestCase):
    def test_disabled_by_default(self) -> None:
        config = StoryCycleConfig().effective()
        self.assertFalse(config.enabled)

    def test_parse_enabled_steps(self) -> None:
        config = StoryCycleConfig.from_mapping(
            {
                "enabled": True,
                "steps": ["atdd", "dev", "verify", "qa"],
                "max_step_retries": 2,
            }
        ).effective()
        self.assertTrue(config.enabled)
        self.assertEqual(config.steps, ("atdd", "dev", "verify", "qa"))
        self.assertEqual(config.max_step_retries, 2)

    def test_rejects_invalid_step(self) -> None:
        with self.assertRaises(ValueError):
            StoryCycleConfig.from_mapping({"enabled": True, "steps": ["deploy"]})


class StoryCycleOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(Story(id=10, title="Cycle", key="1-0-cycle"))
        self.memory = MemoryStore(self.store)
        self.config = StoryCycleConfig(
            enabled=True,
            steps=("dev", "verify", "qa"),
        ).effective()
        self.orchestrator = StoryCycleOrchestrator(self.memory, self.config)

    def tearDown(self) -> None:
        self.store.close()

    def test_advances_through_steps(self) -> None:
        self.assertEqual(self.orchestrator.current_step(10), "dev")
        nxt = self.orchestrator.complete_step(10, "dev")
        self.assertEqual(nxt, "verify")
        self.assertEqual(self.orchestrator.current_step(10), "verify")
        nxt = self.orchestrator.complete_step(10, "verify")
        self.assertEqual(nxt, "qa")
        nxt = self.orchestrator.complete_step(10, "qa")
        self.assertIsNone(nxt)


class SkillLoaderTests(unittest.TestCase):
    def test_load_skill_excerpt_from_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / ".claude" / "skills" / "bmad-bmm-dev-story"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Dev Story\n\nFollow BMAD workflow.\n", encoding="utf-8")

            found = find_skill_dir(root, "dev")
            self.assertIsNotNone(found)
            excerpt = load_skill_excerpt(root, "dev", max_lines=5)
            self.assertIsNotNone(excerpt)
            assert excerpt is not None
            self.assertIn("Dev Story", excerpt.excerpt)
            self.assertIn("bmad-bmm-dev-story", excerpt.skill_path)


if __name__ == "__main__":
    unittest.main()
