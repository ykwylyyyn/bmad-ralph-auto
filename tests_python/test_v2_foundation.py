from __future__ import annotations

from pathlib import Path
import json
import unittest
from http.client import HTTPConnection
import threading
import time

from ralph.api.handlers import ApiHandlers
from ralph.api.server import ApiServer, ApiServerConfig
from ralph.common.db.store import StateStore
from ralph.common.models import Story, StoryState
from ralph.failure.taxonomy import FailureCategory, classify_failure
from ralph.memory.sprint_store import SprintMemoryStore
from ralph.orchestrator.config import OrchestratorConfig
from ralph.orchestrator.controller import FlowPhase, UnifiedOrchestrator
from ralph.router.config import BackendDefinition, RouterConfig
from ralph.router.fallback import FallbackChain
from ralph.router.selector import BackendSelector


class FailureTaxonomyTests(unittest.TestCase):
    def test_classifies_test_failure(self) -> None:
        result = classify_failure("pytest failed with 3 errors")
        self.assertEqual(result.category, FailureCategory.TEST_FAILURE)
        self.assertTrue(result.retryable)

    def test_classifies_spawn_error(self) -> None:
        result = classify_failure("spawn ENOENT: claude not found")
        self.assertEqual(result.category, FailureCategory.SPAWN_ERROR)
        self.assertTrue(result.prefer_worker_restart)

    def test_classifies_verification_failed(self) -> None:
        result = classify_failure("verification failed: make test-all exit code 2")
        self.assertEqual(result.category, FailureCategory.VERIFICATION_FAILED)


class SprintMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StateStore.open_in_memory()
        self.memory = SprintMemoryStore(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_records_modules_and_apis(self) -> None:
        self.memory.add_completed_module("auth")
        self.memory.add_completed_api("POST /login")
        self.assertEqual(self.memory.get_completed_modules(), ["auth"])
        self.assertEqual(self.memory.get_completed_apis(), ["POST /login"])

    def test_build_context_summary(self) -> None:
        self.memory.add_completed_module("billing")
        self.memory.record_failure_pattern("test_failure", "assertion error")
        summary = self.memory.build_context_summary()
        self.assertIn("billing", summary)
        self.assertIn("test_failure", summary)


class RouterFallbackTests(unittest.TestCase):
    def test_fallback_chain_skips_failed_backend(self) -> None:
        selector = BackendSelector(
            RouterConfig(
                default="claude",
                backends={
                    "claude": BackendDefinition(command="claude"),
                    "codex": BackendDefinition(command="codex"),
                    "gpt": BackendDefinition(command="gpt"),
                },
                rules={"dev": "claude"},
                fallback={"dev": ("codex", "gpt")},
            )
        )
        chain = FallbackChain(selector)
        selection = chain.select_with_fallback("dev", failed_backends={"claude"})
        self.assertEqual(selection.backend_name, "codex")
        self.assertGreaterEqual(len(selection.chain), 2)


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(Story(id=1, title="Auth", key="1-1-auth", state=StoryState.IN_REVIEW))

    def tearDown(self) -> None:
        self.store.close()

    def test_auto_done_promotes_in_review(self) -> None:
        orchestrator = UnifiedOrchestrator(
            self.store,
            project_dir=Path("."),
            max_workers=1,
            worktrees_dir=Path("."),
            orchestrator_config=OrchestratorConfig(enabled=True, auto_done=True),
        )
        orchestrator.initialize()
        tick = orchestrator.tick()
        story = self.store.get_story(1)
        self.assertEqual(story.state, StoryState.DONE)
        self.assertEqual(tick.auto_done_count, 1)

    def test_resolve_phase_review_when_in_review_exists(self) -> None:
        orchestrator = UnifiedOrchestrator(
            self.store,
            project_dir=Path("."),
            max_workers=1,
            worktrees_dir=Path("."),
            orchestrator_config=OrchestratorConfig(enabled=True),
        )
        orchestrator.initialize()
        tick = orchestrator.tick()
        self.assertEqual(tick.phase, FlowPhase.REVIEW)


class ApiServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(Story(id=1, title="Demo", key="1-1-demo"))
        self.port = 18765
        self.server = ApiServer(
            ApiServerConfig(enabled=True, host="127.0.0.1", port=self.port),
            lambda: ApiHandlers(self.store, "/tmp/project"),
        )

    def tearDown(self) -> None:
        self.server.stop()
        self.store.close()

    def test_status_endpoint(self) -> None:
        self.server.start()
        time.sleep(0.1)
        conn = HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", "/status")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        conn.close()
        self.assertEqual(response.status, 200)
        self.assertEqual(body["stories"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
