from __future__ import annotations

import logging
import unittest

from ralph.common.db.store import StateStore
from ralph.common.models import HealingLayer, Story, StoryState
from ralph.config import RalphConfig, resolve_config
from ralph.pipeline.healing import HealingOutcomeKind, Layer1StepRetry, StepFailure


class HealingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(
            Story(id=1, title="Retry story", state=StoryState.IN_PROGRESS, worker_id=2)
        )
        self.handler = Layer1StepRetry(self.store, retry_limit=3)

    def tearDown(self) -> None:
        self.store.close()

    def test_step_failure_schedules_retry_on_same_worker(self) -> None:
        outcome = self.handler.handle_step_failure(
            StepFailure(story_id=1, worker_id=2, reason="transient timeout")
        )

        self.assertEqual(outcome.kind, HealingOutcomeKind.RETRY)
        self.assertEqual(outcome.worker_id, 2)
        self.assertEqual(outcome.attempt, 1)

        attempts = self.store.list_healing_attempts(story_id=1)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].layer, HealingLayer.STEP_RETRY)
        self.assertEqual(attempts[0].attempt, 1)
        self.assertEqual(attempts[0].reason, "transient timeout")

    def test_retries_continue_until_limit(self) -> None:
        for attempt in range(1, 4):
            outcome = self.handler.handle_step_failure(
                StepFailure(story_id=1, worker_id=2, reason=f"failure {attempt}")
            )
            self.assertEqual(outcome.kind, HealingOutcomeKind.RETRY)
            self.assertEqual(outcome.attempt, attempt)

        self.assertEqual(self.store.count_healing_attempts(1, HealingLayer.STEP_RETRY), 3)

    def test_exhausted_retries_escalate_to_layer2(self) -> None:
        for _ in range(3):
            self.handler.handle_step_failure(
                StepFailure(story_id=1, worker_id=2, reason="still failing")
            )

        outcome = self.handler.handle_step_failure(
            StepFailure(story_id=1, worker_id=2, reason="final failure")
        )

        self.assertEqual(outcome.kind, HealingOutcomeKind.ESCALATE_LAYER2)
        self.assertEqual(outcome.attempt, 3)
        self.assertEqual(self.store.count_healing_attempts(1, HealingLayer.STEP_RETRY), 3)

    def test_retry_success_records_self_healed_event(self) -> None:
        self.handler.handle_step_failure(
            StepFailure(story_id=1, worker_id=2, reason="transient error")
        )

        outcome = self.handler.handle_retry_success(story_id=1, worker_id=2)

        self.assertEqual(outcome.kind, HealingOutcomeKind.SELF_HEALED)
        attempts = self.store.list_healing_attempts(story_id=1)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[-1].reason, "self-healed")

    def test_healing_activated_logs_warn_with_structured_fields(self) -> None:
        with self.assertLogs("ralph.pipeline.healing.step_retry", level="WARNING") as captured:
            self.handler.handle_step_failure(
                StepFailure(story_id=1, worker_id=2, reason="boom")
            )

        record = captured.records[0]
        self.assertEqual(record.getMessage(), "healing activated")
        self.assertEqual(record.story_id, 1)
        self.assertEqual(record.attempt, 1)
        self.assertEqual(record.layer, "step_retry")

    def test_config_default_retry_limit_is_three(self) -> None:
        self.assertEqual(RalphConfig().retry_limit, None)
        self.assertEqual(RalphConfig().effective().retry_limit, 3)

    def test_resolve_config_reads_retry_limit(self) -> None:
        resolved = resolve_config(overrides=RalphConfig(retry_limit=5))
        self.assertEqual(resolved.retry_limit, 5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
