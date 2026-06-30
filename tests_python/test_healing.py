from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from ralph.common.db.store import StateStore, WorkerRecord
from ralph.common.models import HealingLayer, Story, StoryState, WorkerHealth, WorkerState
from ralph.config import RalphConfig, resolve_config
from ralph.pipeline.healing import (
    DiagnoseRequest,
    HealingOutcomeKind,
    Layer1StepRetry,
    Layer2WorkerRestart,
    Layer3Diagnose,
    StepFailure,
    StoryDiagnoseContext,
    WorkerRestartRequest,
    worker_restart_reason,
)


class FakeWorkerGateway:
    def __init__(self, worktrees_root: Path) -> None:
        self.worktrees_root = worktrees_root
        self.killed: list[int] = []
        self.destroyed: list[int] = []
        self.spawned: list[tuple[int, int]] = []

    def kill_worker(self, worker_id: int) -> None:
        self.killed.append(worker_id)

    def destroy_worktree(self, worker_id: int) -> None:
        self.destroyed.append(worker_id)
        worktree = self.worktrees_root / f"worker-{worker_id}"
        if worktree.exists():
            for child in sorted(worktree.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
            worktree.rmdir()

    def spawn_fresh(self, worker_id: int, story: Story) -> Path:
        self.spawned.append((worker_id, story.id))
        worktree = self.worktrees_root / f"worker-{worker_id}"
        worktree.mkdir(parents=True, exist_ok=True)
        (worktree / ".ralph-fresh").write_text("clean", encoding="utf-8")
        return worktree


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


class Layer2WorkerRestartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.worktrees_root = Path(self.temp_dir.name)
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(
            Story(id=1, title="Restart story", state=StoryState.IN_PROGRESS, worker_id=2)
        )
        self.store.upsert_worker(
            WorkerRecord(
                id=2,
                state=WorkerState.RUNNING,
                health=WorkerHealth.DEGRADED,
                worktree_path="/tmp/worker-2-old",
                pid=4242,
            )
        )
        self.gateway = FakeWorkerGateway(self.worktrees_root)
        self.handler = Layer2WorkerRestart(self.store, self.gateway)

    def tearDown(self) -> None:
        self.store.close()
        self.temp_dir.cleanup()

    def test_escalation_kills_worker_destroys_worktree_and_spawns_fresh(self) -> None:
        outcome = self.handler.handle_escalation(
            WorkerRestartRequest(story_id=1, worker_id=2, reason="layer 1 exhausted")
        )

        self.assertEqual(outcome.kind, HealingOutcomeKind.RESTART)
        self.assertEqual(outcome.old_worker_id, 2)
        self.assertEqual(outcome.new_worker_id, 2)
        self.assertEqual(self.gateway.killed, [2])
        self.assertEqual(self.gateway.destroyed, [2])
        self.assertEqual(self.gateway.spawned, [(2, 1)])

        worker = self.store.get_worker(2)
        self.assertEqual(worker.state, WorkerState.RUNNING)
        self.assertNotEqual(worker.worktree_path, "/tmp/worker-2-old")
        self.assertTrue(Path(worker.worktree_path).joinpath(".ralph-fresh").exists())

        story = self.store.get_story(1)
        self.assertEqual(story.state, StoryState.IN_PROGRESS)
        self.assertEqual(story.worker_id, 2)

    def test_restart_records_healing_attempt_with_worker_ids(self) -> None:
        self.handler.handle_escalation(
            WorkerRestartRequest(story_id=1, worker_id=2, reason="layer 1 exhausted")
        )

        attempts = self.store.list_healing_attempts(story_id=1)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].layer, HealingLayer.WORKER_RESTART)
        self.assertEqual(attempts[0].reason, worker_restart_reason(2, 2))

    def test_restart_requeues_story_before_fresh_spawn(self) -> None:
        observed_states: list[StoryState] = []
        store = self.store

        class TrackingGateway(FakeWorkerGateway):
            def spawn_fresh(self, worker_id: int, story: Story) -> Path:
                observed_states.append(store.get_story(story.id).state)
                return super().spawn_fresh(worker_id, story)

        with tempfile.TemporaryDirectory() as tmp:
            gateway = TrackingGateway(Path(tmp))
            handler = Layer2WorkerRestart(store, gateway)

            handler.handle_escalation(
                WorkerRestartRequest(story_id=1, worker_id=2, reason="layer 1 exhausted")
            )

        self.assertEqual(observed_states, [StoryState.QUEUED])

    def test_restart_success_marks_story_done_and_records_self_healed(self) -> None:
        self.handler.handle_escalation(
            WorkerRestartRequest(story_id=1, worker_id=2, reason="layer 1 exhausted")
        )

        outcome = self.handler.handle_restart_success(story_id=1, worker_id=2)

        self.assertEqual(outcome.kind, HealingOutcomeKind.SELF_HEALED)
        story = self.store.get_story(1)
        self.assertEqual(story.state, StoryState.DONE)
        attempts = self.store.list_healing_attempts(story_id=1)
        self.assertEqual(attempts[-1].reason, "self-healed")

    def test_restart_failure_escalates_to_layer3(self) -> None:
        self.handler.handle_escalation(
            WorkerRestartRequest(story_id=1, worker_id=2, reason="layer 1 exhausted")
        )

        outcome = self.handler.handle_restart_failure(
            WorkerRestartRequest(story_id=1, worker_id=2, reason="fresh worker failed")
        )

        self.assertEqual(outcome.kind, HealingOutcomeKind.ESCALATE_LAYER3)
        self.assertEqual(outcome.reason, "fresh worker failed")

    def test_layer1_to_layer2_handoff(self) -> None:
        layer1 = Layer1StepRetry(self.store, retry_limit=2)
        for _ in range(2):
            layer1.handle_step_failure(StepFailure(story_id=1, worker_id=2, reason="fail"))

        escalation = layer1.handle_step_failure(
            StepFailure(story_id=1, worker_id=2, reason="final fail")
        )
        self.assertEqual(escalation.kind, HealingOutcomeKind.ESCALATE_LAYER2)

        restart = self.handler.handle_escalation(
            WorkerRestartRequest(
                story_id=escalation.story_id,
                worker_id=escalation.worker_id,
                reason=escalation.reason or "escalated",
            )
        )
        self.assertEqual(restart.kind, HealingOutcomeKind.RESTART)

    def test_healing_activated_logs_warn_for_worker_restart(self) -> None:
        with self.assertLogs("ralph.pipeline.healing.worker_restart", level="WARNING") as captured:
            self.handler.handle_escalation(
                WorkerRestartRequest(story_id=1, worker_id=2, reason="layer 1 exhausted")
            )

        record = captured.records[0]
        self.assertEqual(record.getMessage(), "healing activated")
        self.assertEqual(record.layer, "worker_restart")


class Layer3DiagnoseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.worktrees_root = Path(self.temp_dir.name)
        self.store = StateStore.open_in_memory()
        self.store.upsert_story(
            Story(id=7, title="Diagnose story", state=StoryState.IN_PROGRESS, worker_id=2)
        )
        self.store.upsert_worker(
            WorkerRecord(
                id=2,
                state=WorkerState.RUNNING,
                health=WorkerHealth.DEGRADED,
                worktree_path="/tmp/worker-2-old",
            )
        )
        self.layer1 = Layer1StepRetry(self.store, retry_limit=1)
        self.layer2 = Layer2WorkerRestart(self.store, FakeWorkerGateway(self.worktrees_root))
        self.layer3 = Layer3Diagnose(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp_dir.cleanup()

    def _escalate_through_layer2(self) -> None:
        self.layer1.handle_step_failure(StepFailure(story_id=7, worker_id=2, reason="timeout"))
        escalation = self.layer1.handle_step_failure(
            StepFailure(story_id=7, worker_id=2, reason="timeout again")
        )
        self.assertEqual(escalation.kind, HealingOutcomeKind.ESCALATE_LAYER2)
        self.layer2.handle_escalation(
            WorkerRestartRequest(
                story_id=7,
                worker_id=2,
                reason=escalation.reason or "layer 1 exhausted",
            )
        )
        layer3_escalation = self.layer2.handle_restart_failure(
            WorkerRestartRequest(story_id=7, worker_id=2, reason="fresh worker failed")
        )
        self.assertEqual(layer3_escalation.kind, HealingOutcomeKind.ESCALATE_LAYER3)

    def test_escalation_triggers_diagnose_and_marks_story_failed(self) -> None:
        self._escalate_through_layer2()

        outcome = self.layer3.handle_escalation(
            DiagnoseRequest(story_id=7, worker_id=2, reason="fresh worker failed"),
            context=StoryDiagnoseContext(
                acceptance_criteria=["Must pass tests"],
                log_excerpt=["ERROR: build failed", "worker exited"],
            ),
        )

        self.assertEqual(outcome.kind, HealingOutcomeKind.EXHAUSTED)
        story = self.store.get_story(7)
        self.assertEqual(story.state, StoryState.FAILED)
        self.assertIsNone(story.worker_id)

    def test_diagnose_stores_structured_report(self) -> None:
        self._escalate_through_layer2()

        self.layer3.handle_escalation(
            DiagnoseRequest(story_id=7, worker_id=2, reason="fresh worker failed"),
            context=StoryDiagnoseContext(
                acceptance_criteria=["Must pass tests"],
                log_excerpt=["ERROR: build failed"],
            ),
        )

        report = self.store.get_diagnostic_report(7)
        self.assertIn("exhausted all healing layers", report.root_cause)
        self.assertIn("Review failure patterns", report.recommendation)
        self.assertEqual(report.suggested_fix, "ralph retry 7")
        self.assertIn("failure_patterns", report.analysis)
        self.assertIn("step_retry", report.analysis["healing_layers_attempted"])
        self.assertIn("worker_restart", report.analysis["healing_layers_attempted"])
        self.assertIn("diagnose", report.analysis["healing_layers_attempted"])

    def test_diagnose_records_layer3_healing_attempt(self) -> None:
        self._escalate_through_layer2()
        self.layer3.handle_escalation(
            DiagnoseRequest(story_id=7, worker_id=2, reason="fresh worker failed")
        )

        attempts = self.store.list_healing_attempts(story_id=7)
        diagnose_attempts = [item for item in attempts if item.layer == HealingLayer.DIAGNOSE]
        self.assertEqual(len(diagnose_attempts), 1)
        self.assertEqual(diagnose_attempts[0].reason, "diagnose flow triggered")

    def test_full_layer1_to_layer3_handoff_preserves_healing_history(self) -> None:
        self._escalate_through_layer2()
        self.layer3.handle_escalation(
            DiagnoseRequest(story_id=7, worker_id=2, reason="fresh worker failed")
        )

        attempts = self.store.list_healing_attempts(story_id=7)
        layers = {attempt.layer for attempt in attempts}
        self.assertEqual(
            layers,
            {HealingLayer.STEP_RETRY, HealingLayer.WORKER_RESTART, HealingLayer.DIAGNOSE},
        )
        self.assertGreaterEqual(len(attempts), 3)

    def test_healing_activated_logs_warn_for_diagnose(self) -> None:
        self._escalate_through_layer2()
        with self.assertLogs("ralph.pipeline.healing.diagnose", level="WARNING") as captured:
            self.layer3.handle_escalation(
                DiagnoseRequest(story_id=7, worker_id=2, reason="fresh worker failed")
            )

        record = captured.records[0]
        self.assertEqual(record.getMessage(), "healing activated")
        self.assertEqual(record.layer, "diagnose")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
