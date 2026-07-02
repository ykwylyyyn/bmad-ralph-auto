from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ralph.common.db.store import StateStore
from ralph.common.models import PipelineState, Story, StoryState
from ralph.failure.taxonomy import classify_failure
from ralph.memory.sprint_store import SprintMemoryStore
from ralph.pipeline.healing.diagnose import DiagnoseRequest, Layer3Diagnose, StoryDiagnoseContext
from ralph.pipeline.healing.step_retry import Layer1StepRetry, StepFailure
from ralph.pipeline.healing.types import HealingOutcomeKind
from ralph.pipeline.healing.worker_restart import Layer2WorkerRestart, WorkerRestartGateway, WorkerRestartRequest
from ralph.worker.manager import WorkerManager
from ralph.worker.worktree import GitWorktreeManager, story_branch_name


class EngineRestartGateway:
    """Adapter that lets Layer 2 restart workers through the pipeline engine."""

    def __init__(
        self,
        store: StateStore,
        manager: WorkerManager,
        worktrees_dir: Path,
        worktree_manager: GitWorktreeManager | None = None,
    ) -> None:
        self._store = store
        self._manager = manager
        self._worktrees_dir = worktrees_dir
        self._worktrees = worktree_manager or GitWorktreeManager()

    def kill_worker(self, worker_id: int) -> None:
        if worker_id in self._manager.active_sessions:
            self._manager.kill_worker(worker_id)

    def destroy_worktree(self, worker_id: int) -> None:
        worker = self._store.get_worker(worker_id)
        worktree_path = Path(worker.worktree_path)
        story_id = self._story_id_for_worker(worker_id)
        if story_id is None:
            return
        story = self._store.get_story(story_id)
        branch = story_branch_name(story.id, story.key)
        project_dir = self._manager._project_dir  # noqa: SLF001 — gateway is engine-internal
        self._worktrees.destroy(project_dir, worktree_path, branch)

    def spawn_fresh(self, worker_id: int, story: Story) -> Path:
        active = self._manager.spawn_for_story(worker_id, story)
        return active.worktree_path

    def _story_id_for_worker(self, worker_id: int) -> int | None:
        active = self._manager.active_sessions.get(worker_id)
        if active is not None:
            return active.story_id
        for story in self._store.list_stories():
            if story.worker_id == worker_id:
                return story.id
        return None


class HealingCoordinator:
    """Routes story failures through Layer 1 → Layer 2 → Layer 3 self-healing."""

    def __init__(
        self,
        store: StateStore,
        *,
        retry_limit: int,
        gateway: WorkerRestartGateway,
    ) -> None:
        self._store = store
        self._layer1 = Layer1StepRetry(store, retry_limit=retry_limit)
        self._layer2 = Layer2WorkerRestart(store, gateway)
        self._layer3 = Layer3Diagnose(store)

    def handle_failure(
        self,
        *,
        story_id: int,
        worker_id: int,
        reason: str,
        log_excerpt: list[str] | None = None,
    ) -> None:
        classification = classify_failure(reason, log_excerpt=log_excerpt)
        sprint_memory = SprintMemoryStore(self._store)
        sprint_memory.record_failure_pattern(classification.category.value, reason)
        self._store.record_pipeline_event(
            "failure_classified",
            {
                "story_id": story_id,
                "worker_id": worker_id,
                "category": classification.category.value,
                "confidence": classification.confidence,
                "retryable": classification.retryable,
                "prefer_worker_restart": classification.prefer_worker_restart,
            },
        )

        if classification.prefer_worker_restart:
            restart = self._layer2.handle_escalation(
                WorkerRestartRequest(
                    story_id=story_id,
                    worker_id=worker_id,
                    reason=f"[{classification.category.value}] {reason}",
                )
            )
            if restart.kind == HealingOutcomeKind.ESCALATE_LAYER3:
                self._escalate_to_diagnose(
                    story_id,
                    worker_id,
                    restart.reason or reason,
                    log_excerpt,
                    classification.category.value,
                )
            else:
                self._store.set_pipeline_state(PipelineState.HEALING)
            return

        failure = StepFailure(story_id=story_id, worker_id=worker_id, reason=reason)
        outcome = self._layer1.handle_step_failure(failure)

        if outcome.kind == HealingOutcomeKind.RETRY:
            self._store.requeue_story(story_id)
            self._store.set_pipeline_state(PipelineState.HEALING)
            return

        if outcome.kind == HealingOutcomeKind.ESCALATE_LAYER2:
            restart = self._layer2.handle_escalation(
                WorkerRestartRequest(
                    story_id=story_id,
                    worker_id=worker_id,
                    reason=outcome.reason or reason,
                )
            )
            if restart.kind == HealingOutcomeKind.ESCALATE_LAYER3:
                self._escalate_to_diagnose(story_id, worker_id, restart.reason or reason, log_excerpt)
            else:
                self._store.set_pipeline_state(PipelineState.HEALING)
            return

        self._mark_failed(story_id, reason)

    def _escalate_to_diagnose(
        self,
        story_id: int,
        worker_id: int,
        reason: str,
        log_excerpt: list[str] | None,
        failure_category: str | None = None,
    ) -> None:
        story = self._store.get_story(story_id)
        context = StoryDiagnoseContext(
            acceptance_criteria=list(story.acceptance_criteria),
            log_excerpt=log_excerpt or [],
        )
        outcome = self._layer3.handle_escalation(
            DiagnoseRequest(story_id=story_id, worker_id=worker_id, reason=reason),
            context=context,
        )
        if failure_category:
            self._store.record_pipeline_event(
                "diagnose_with_category",
                {"story_id": story_id, "category": failure_category},
            )
        if outcome.kind == HealingOutcomeKind.EXHAUSTED:
            pass  # Layer 3 already marks the story failed.
        self._store.set_pipeline_state(PipelineState.HEALING)

    def _mark_failed(self, story_id: int, reason: str) -> None:
        story = self._store.get_story(story_id)
        if story.state not in {StoryState.DONE, StoryState.FAILED}:
            self._store.transition_story_state(story_id, StoryState.FAILED)
        self._store.record_pipeline_event(
            "story_failed",
            {"story_id": story_id, "reason": reason},
        )
