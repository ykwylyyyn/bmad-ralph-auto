from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ralph.common.db.store import StateStore, WorkerRecord
from ralph.common.models import PipelineState, Story, StoryState, WorkerHealth, WorkerState
from ralph.pipeline.dependency_graph import DependencyGraph
from ralph.memory.progress import sync_story_progress
from ralph.memory.store import MemoryStore
from ralph.pipeline.healing.coordinator import EngineRestartGateway, HealingCoordinator
from ralph.pipeline.ingestion import build_dependency_graph
from ralph.pipeline.orchestrator import StoryCycleOrchestrator
from ralph.pipeline.recovery import recover_orphaned_stories
from ralph.pipeline.scheduler import StoryScheduler
from ralph.pipeline.story_cycle import StoryCycleConfig
from ralph.verifier import VerifierConfig, VerifierRunner
from ralph.worker.errors import WorkerSpawnError
from ralph.worker.manager import WorkerExit, WorkerManager, story_state_for_result
from ralph.worker.prompt import build_step_prompt, load_prompt_context

_TERMINAL_STORY_STATES = {StoryState.DONE, StoryState.FAILED}
_ACTIVE_STORY_STATES = {
    StoryState.IN_PROGRESS,
    StoryState.VERIFYING,
    StoryState.IN_REVIEW,
}


@dataclass(frozen=True, slots=True)
class AssignmentResult:
    story_id: int
    worker_id: int


@dataclass(frozen=True, slots=True)
class SpawnFailure:
    story_id: int
    worker_id: int
    reason: str


@dataclass(slots=True)
class PipelineTickResult:
    pipeline_state: PipelineState
    assignments: list[AssignmentResult] = field(default_factory=list)
    completions: list[WorkerExit] = field(default_factory=list)
    worker_failures: list[WorkerExit] = field(default_factory=list)
    spawn_failures: list[SpawnFailure] = field(default_factory=list)
    schedulable_count: int = 0
    active_workers: int = 0
    completed_stories: int = 0
    sprint_completed: bool = False


class PipelineEngine:
    """Orchestrates story scheduling, worker spawning, and pipeline state transitions."""

    def __init__(
        self,
        store: StateStore,
        *,
        project_dir: Path,
        max_workers: int,
        worktrees_dir: Path,
        logs_dir: Path | None = None,
        worker_manager: WorkerManager | None = None,
        retry_limit: int = 3,
        verifier_config: VerifierConfig | None = None,
        story_cycle_config: StoryCycleConfig | None = None,
    ) -> None:
        self._store = store
        self._project_dir = project_dir.resolve()
        self._scheduler = StoryScheduler(max_workers)
        self._worktrees_dir = worktrees_dir
        self._logs_dir = logs_dir
        self._worker_manager = worker_manager or WorkerManager(
            project_dir,
            worktrees_dir,
            logs_dir=logs_dir,
        )
        self._graph: DependencyGraph | None = None
        self._cycle_config = (story_cycle_config or StoryCycleConfig()).effective()
        self._memory = MemoryStore(store)
        self._orchestrator = StoryCycleOrchestrator(self._memory, self._cycle_config)
        self._verifier = VerifierRunner(verifier_config or VerifierConfig())
        restart_gateway = EngineRestartGateway(
            store,
            self._worker_manager,
            worktrees_dir,
        )
        self._healing = HealingCoordinator(
            store,
            retry_limit=retry_limit,
            gateway=restart_gateway,
        )

    @property
    def worker_manager(self) -> WorkerManager:
        return self._worker_manager

    def initialize(self) -> PipelineState:
        stories = self._store.list_stories()
        if not stories:
            self._store.set_pipeline_state(PipelineState.IDLE)
            return PipelineState.IDLE

        recover_orphaned_stories(
            self._store,
            active_worker_ids=set(self._worker_manager.active_sessions),
        )

        stories = self._store.list_stories()
        self._graph = build_dependency_graph(stories)
        self._ensure_worker_pool()
        state = self._evaluate_pipeline_state(stories)
        self._store.set_pipeline_state(state)
        return state

    def shutdown(self) -> None:
        for story in self._store.list_stories():
            if story.state == StoryState.IN_PROGRESS:
                try:
                    self._store.rollback_story_assignment(story.id)
                except Exception:
                    continue
            elif story.state == StoryState.VERIFYING:
                try:
                    self._store.requeue_story(story.id)
                except Exception:
                    continue

        self._worker_manager.shutdown()

        for worker in self._store.list_workers():
            if worker.state == WorkerState.IDLE and worker.health == WorkerHealth.HEALTHY:
                continue
            self._store.upsert_worker(
                WorkerRecord(
                    id=worker.id,
                    state=WorkerState.IDLE,
                    health=WorkerHealth.HEALTHY,
                    worktree_path=worker.worktree_path,
                    pid=None,
                )
            )

    def kill_worker(self, worker_id: int) -> bool:
        exit_event = self._worker_manager.kill_worker(worker_id)
        if exit_event is None:
            return False

        story = self._store.get_story(exit_event.story_id)
        if story.state == StoryState.IN_PROGRESS:
            self._store.rollback_story_assignment(exit_event.story_id)

        self._store.upsert_worker(
            WorkerRecord(
                id=worker_id,
                state=WorkerState.FAILED,
                health=WorkerHealth.DEGRADED,
                worktree_path=str(self._worktrees_dir / f"worker-{worker_id}"),
                pid=None,
            )
        )
        self._store.record_pipeline_event(
            "worker_killed",
            {
                "worker_id": worker_id,
                "story_id": exit_event.story_id,
                "exit_code": exit_event.exit_code,
            },
        )
        return True

    def tick(self) -> PipelineTickResult:
        self._sync_worker_health_to_db()

        completions: list[WorkerExit] = []
        worker_failures: list[WorkerExit] = []
        for exit_event in self._worker_manager.poll_exits():
            if exit_event.exit_kind == "completed":
                self._handle_completion(exit_event)
                completions.append(exit_event)
            elif exit_event.exit_kind == "unexpected":
                self._handle_unexpected_exit(exit_event)
                worker_failures.append(exit_event)
            else:
                self._handle_killed_exit(exit_event)
                worker_failures.append(exit_event)

        stories = self._store.list_stories()
        if not stories:
            self._store.set_pipeline_state(PipelineState.IDLE)
            return PipelineTickResult(
                pipeline_state=PipelineState.IDLE,
                completions=completions,
                worker_failures=worker_failures,
            )

        if self._graph is None:
            self._graph = build_dependency_graph(stories)

        self._ensure_worker_pool()
        workers = self._store.list_workers()
        snapshot = self._scheduler.evaluate(stories, workers)

        assignments: list[AssignmentResult] = []
        spawn_failures: list[SpawnFailure] = []
        idle_workers = self._scheduler.idle_workers(workers)
        for story, worker in zip(snapshot.schedulable, idle_workers):
            if len(assignments) >= snapshot.available_slots:
                break

            step = self._orchestrator.current_step(story.id)
            if self._orchestrator.enabled and self._orchestrator.is_verify_step(step):
                worktree_raw = self._memory.get_worktree_path(story.id)
                if worktree_raw is None:
                    next_step = self._orchestrator.complete_step(story.id, step)
                    if next_step is None:
                        self._store.transition_story_state(story.id, StoryState.IN_REVIEW)
                        self._sync_progress_for_story(story.id, step, cycle_complete=True)
                    continue

                self._store.assign_story_to_worker(story.id, worker.id)
                self._run_cycle_verify(story.id, worker.id, Path(worktree_raw))
                assignments.append(AssignmentResult(story_id=story.id, worker_id=worker.id))
                continue

            self._store.assign_story_to_worker(story.id, worker.id)
            try:
                prompt = self._build_prompt_for_story(story, step)
                worktree_raw = self._memory.get_worktree_path(story.id)
                active = self._worker_manager.spawn_for_story(
                    worker.id,
                    story,
                    prompt=prompt,
                    worktree_path=Path(worktree_raw) if worktree_raw else None,
                )
            except WorkerSpawnError as exc:
                self._store.rollback_story_assignment(story.id)
                self._store.upsert_worker(
                    WorkerRecord(
                        id=worker.id,
                        state=WorkerState.IDLE,
                        health=WorkerHealth.DEGRADED,
                        worktree_path=worker.worktree_path,
                        pid=None,
                    )
                )
                self._store.record_pipeline_event(
                    "worker_spawn_failed",
                    {
                        "story_id": story.id,
                        "worker_id": worker.id,
                        "reason": exc.reason,
                    },
                )
                spawn_failures.append(
                    SpawnFailure(story_id=story.id, worker_id=worker.id, reason=exc.reason)
                )
                continue

            if self._orchestrator.enabled and self._memory.get_worktree_path(story.id) is None:
                self._memory.set_worktree_path(story.id, str(active.worktree_path))

            self._store.upsert_worker(
                WorkerRecord(
                    id=worker.id,
                    state=WorkerState.RUNNING,
                    health=WorkerHealth.HEALTHY,
                    worktree_path=str(active.worktree_path),
                    pid=active.session.pid,
                )
            )
            assignments.append(AssignmentResult(story_id=story.id, worker_id=worker.id))

        self._sync_worker_health_to_db()
        self._recover_failed_workers()

        stories = self._store.list_stories()
        pipeline_state = self._evaluate_pipeline_state(stories)
        self._store.set_pipeline_state(pipeline_state)

        completed = sum(1 for story in stories if story.state == StoryState.DONE)
        sprint_completed = pipeline_state == PipelineState.COMPLETE
        if sprint_completed:
            self._store.record_pipeline_event(
                "sprint_complete",
                {
                    "completed_stories": completed,
                    "failed_stories": sum(1 for story in stories if story.state == StoryState.FAILED),
                    "total_stories": len(stories),
                },
            )

        workers = self._store.list_workers()
        return PipelineTickResult(
            pipeline_state=pipeline_state,
            assignments=assignments,
            completions=completions,
            worker_failures=worker_failures,
            spawn_failures=spawn_failures,
            schedulable_count=len(snapshot.schedulable),
            active_workers=self._scheduler.active_worker_count(workers),
            completed_stories=completed,
            sprint_completed=sprint_completed,
        )

    def status_message(self, tick: PipelineTickResult) -> str:
        if tick.pipeline_state == PipelineState.COMPLETE:
            return f"pipeline complete: {tick.completed_stories} stories done"
        if tick.worker_failures:
            failure = tick.worker_failures[0]
            return (
                f"pipeline running: worker {failure.worker_id} "
                f"exit ({failure.exit_kind}) for story #{failure.story_id}"
            )
        if tick.spawn_failures:
            failure = tick.spawn_failures[0]
            return f"pipeline running: spawn failed for story #{failure.story_id} ({failure.reason})"
        if tick.assignments:
            assigned = ", ".join(f"#{item.story_id}->W{item.worker_id}" for item in tick.assignments)
            return f"pipeline running: spawned {assigned}"
        if tick.completions:
            return f"pipeline running: {len(tick.completions)} worker(s) finished"
        return (
            f"pipeline {tick.pipeline_state.value}: "
            f"{tick.schedulable_count} schedulable, {tick.active_workers} active workers"
        )

    def _handle_completion(self, exit_event: WorkerExit) -> None:
        if exit_event.result is None:
            return

        story = self._store.get_story(exit_event.story_id)
        if story.state != StoryState.IN_PROGRESS:
            return

        target_state = story_state_for_result(exit_event.result)
        if target_state == StoryState.FAILED:
            self._release_worker(exit_event.worker_id)
            self._healing.handle_failure(
                story_id=exit_event.story_id,
                worker_id=exit_event.worker_id,
                reason=exit_event.result.error or "worker reported failure",
                log_excerpt=self._log_excerpt(exit_event),
            )
            if not self._orchestrator.enabled or not self._orchestrator.has_more_steps(exit_event.story_id):
                self._worker_manager.release_worktree(exit_event)
            return

        if self._orchestrator.enabled:
            self._handle_cycle_completion(exit_event)
            return

        self._handle_legacy_completion(exit_event)

    def _handle_legacy_completion(self, exit_event: WorkerExit) -> None:
        self._release_worker(exit_event.worker_id)

        if self._verifier.enabled:
            self._store.transition_story_state(exit_event.story_id, StoryState.VERIFYING)
            self._verify_and_finish(exit_event)
            self._worker_manager.release_worktree(exit_event)
            return

        self._store.transition_story_state(exit_event.story_id, StoryState.IN_REVIEW)
        self._worker_manager.release_worktree(exit_event)

    def _handle_cycle_completion(self, exit_event: WorkerExit) -> None:
        step = self._orchestrator.current_step(exit_event.story_id)
        self._memory.append_event(
            exit_event.story_id,
            {"type": "step_complete", "step": step},
        )
        self._sync_progress_for_story(exit_event.story_id, step)

        next_step = self._orchestrator.complete_step(exit_event.story_id, step)
        self._release_worker(exit_event.worker_id)
        self._memory.set_worktree_path(exit_event.story_id, str(exit_event.worktree_path))

        if next_step is None:
            self._store.transition_story_state(exit_event.story_id, StoryState.IN_REVIEW)
            self._sync_progress_for_story(exit_event.story_id, step, cycle_complete=True)
            self._memory.clear_cycle(exit_event.story_id)
            self._worker_manager.release_worktree(exit_event)
            return

        self._store.requeue_story(exit_event.story_id)

    def _run_cycle_verify(self, story_id: int, worker_id: int, worktree_path: Path) -> None:
        if not self._verifier.enabled:
            next_step = self._orchestrator.complete_step(story_id, "verify")
            self._sync_progress_for_story(story_id, "verify", cycle_complete=next_step is None)
            self._finish_cycle_step(story_id, worker_id, worktree_path, next_step)
            return

        self._store.transition_story_state(story_id, StoryState.VERIFYING)
        result = self._verifier.run(worktree_path)
        if result.passed:
            self._memory.append_event(story_id, {"type": "verify_passed"})
            self._store.record_pipeline_event(
                "verification_passed",
                {"story_id": story_id, "step": "verify"},
            )
            next_step = self._orchestrator.complete_step(story_id, "verify")
            self._sync_progress_for_story(story_id, "verify", cycle_complete=next_step is None)
            self._finish_cycle_step(story_id, worker_id, worktree_path, next_step)
            return

        log_excerpt = [failure.stderr for failure in result.failures if failure.stderr]
        self._release_worker(worker_id)
        self._healing.handle_failure(
            story_id=story_id,
            worker_id=worker_id,
            reason=result.summary,
            log_excerpt=log_excerpt,
        )
        self._store.record_pipeline_event(
            "verification_failed",
            {
                "story_id": story_id,
                "summary": result.summary,
                "failures": [
                    {
                        "command": failure.command,
                        "exit_code": failure.exit_code,
                        "stderr": failure.stderr,
                    }
                    for failure in result.failures
                ],
            },
        )

    def _finish_cycle_step(
        self,
        story_id: int,
        worker_id: int,
        worktree_path: Path,
        next_step: str | None,
    ) -> None:
        self._release_worker(worker_id)
        if next_step is None:
            self._store.transition_story_state(story_id, StoryState.IN_REVIEW)
            self._memory.clear_cycle(story_id)
            exit_event = WorkerExit(
                worker_id=worker_id,
                story_id=story_id,
                result=None,
                exit_kind="completed",
                exit_code=0,
                branch="",
                worktree_path=worktree_path,
            )
            self._worker_manager.release_worktree(exit_event)
            return
        self._store.requeue_story(story_id)
        self._memory.set_worktree_path(story_id, str(worktree_path))

    def _build_prompt_for_story(self, story: Story, step: str) -> str:
        progress = self._memory.get_progress(story.id)
        events = progress.get("events", [])
        memory_events = events if isinstance(events, list) else []
        context = load_prompt_context(
            self._project_dir,
            story,
            step,
            memory_events=memory_events,
            max_chars=self._cycle_config.prompt_max_chars,
        )
        return build_step_prompt(story, step, context)

    def _sync_progress_for_story(
        self,
        story_id: int,
        step: str,
        *,
        cycle_complete: bool = False,
    ) -> None:
        story = self._store.get_story(story_id)
        if not story.key:
            return
        sync_story_progress(
            self._project_dir,
            story.key,
            step,
            artifacts_dir=self._cycle_config.artifacts_dir,
            cycle_complete=cycle_complete,
        )

    def _verify_and_finish(self, exit_event: WorkerExit) -> None:
        story = self._store.get_story(exit_event.story_id)
        if story.state != StoryState.VERIFYING:
            return

        result = self._verifier.run(exit_event.worktree_path)
        if result.passed:
            self._store.transition_story_state(exit_event.story_id, StoryState.DONE)
            self._store.record_pipeline_event(
                "verification_passed",
                {"story_id": exit_event.story_id},
            )
            return

        log_excerpt = [failure.stderr for failure in result.failures if failure.stderr]
        self._healing.handle_failure(
            story_id=exit_event.story_id,
            worker_id=exit_event.worker_id,
            reason=result.summary,
            log_excerpt=log_excerpt,
        )
        self._store.record_pipeline_event(
            "verification_failed",
            {
                "story_id": exit_event.story_id,
                "summary": result.summary,
                "failures": [
                    {
                        "command": failure.command,
                        "exit_code": failure.exit_code,
                        "stderr": failure.stderr,
                    }
                    for failure in result.failures
                ],
            },
        )

    def _handle_unexpected_exit(self, exit_event: WorkerExit) -> None:
        story = self._store.get_story(exit_event.story_id)
        if story.state != StoryState.IN_PROGRESS:
            return

        self._release_worker(exit_event.worker_id, health=WorkerHealth.DEGRADED, state=WorkerState.FAILED)
        self._healing.handle_failure(
            story_id=exit_event.story_id,
            worker_id=exit_event.worker_id,
            reason=f"unexpected worker exit (code {exit_event.exit_code})",
            log_excerpt=self._log_excerpt(exit_event),
        )
        self._store.record_pipeline_event(
            "worker_exit_unexpected",
            {
                "worker_id": exit_event.worker_id,
                "story_id": exit_event.story_id,
                "exit_code": exit_event.exit_code,
                "log_path": str(exit_event.log_path) if exit_event.log_path else None,
            },
        )

    def _handle_killed_exit(self, exit_event: WorkerExit) -> None:
        story = self._store.get_story(exit_event.story_id)
        if story.state == StoryState.IN_PROGRESS:
            self._store.rollback_story_assignment(exit_event.story_id)
        self._release_worker(exit_event.worker_id, health=WorkerHealth.DEGRADED, state=WorkerState.FAILED)
        self._store.record_pipeline_event(
            "worker_killed",
            {
                "worker_id": exit_event.worker_id,
                "story_id": exit_event.story_id,
                "exit_code": exit_event.exit_code,
            },
        )

    def _release_worker(
        self,
        worker_id: int,
        *,
        health: WorkerHealth = WorkerHealth.HEALTHY,
        state: WorkerState = WorkerState.IDLE,
    ) -> None:
        self._store.upsert_worker(
            WorkerRecord(
                id=worker_id,
                state=state,
                health=health,
                worktree_path=str(self._worktrees_dir / f"worker-{worker_id}"),
                pid=None,
            )
        )

    def _log_excerpt(self, exit_event: WorkerExit) -> list[str]:
        if exit_event.log_path is None or not exit_event.log_path.is_file():
            return []
        try:
            lines = exit_event.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
        return [line for line in lines[-20:] if line.strip()]

    def _sync_worker_health_to_db(self) -> None:
        active_reports = {item.worker_id: item for item in self._worker_manager.check_health()}
        active_ids = set(active_reports)

        for worker_id, report in active_reports.items():
            active = self._worker_manager.active_sessions[worker_id]
            self._store.upsert_worker(
                WorkerRecord(
                    id=worker_id,
                    state=WorkerState.RUNNING,
                    health=report.health,
                    worktree_path=str(active.worktree_path),
                    pid=report.pid,
                )
            )

        for worker in self._store.list_workers():
            if worker.id in active_ids:
                continue
            if worker.state == WorkerState.RUNNING:
                self._store.upsert_worker(
                    WorkerRecord(
                        id=worker.id,
                        state=WorkerState.IDLE,
                        health=WorkerHealth.DEGRADED,
                        worktree_path=str(self._worktrees_dir / f"worker-{worker.id}"),
                        pid=None,
                    )
                )
            elif worker.state == WorkerState.IDLE:
                self._store.upsert_worker(
                    WorkerRecord(
                        id=worker.id,
                        state=WorkerState.IDLE,
                        health=WorkerHealth.HEALTHY,
                        worktree_path=worker.worktree_path,
                        pid=None,
                    )
                )

    def _recover_failed_workers(self) -> None:
        active_ids = set(self._worker_manager.active_sessions)
        for worker in self._store.list_workers():
            if worker.state != WorkerState.FAILED:
                continue
            if worker.id in active_ids:
                continue
            self._store.upsert_worker(
                WorkerRecord(
                    id=worker.id,
                    state=WorkerState.IDLE,
                    health=WorkerHealth.DEGRADED,
                    worktree_path=str(self._worktrees_dir / f"worker-{worker.id}"),
                    pid=None,
                )
            )

    def _ensure_worker_pool(self) -> None:
        workers = self._store.list_workers()
        existing_ids = {worker.id for worker in workers}
        for worker_id in range(1, self._scheduler.max_workers + 1):
            if worker_id in existing_ids:
                continue
            self._store.upsert_worker(
                WorkerRecord(
                    id=worker_id,
                    state=WorkerState.IDLE,
                    health=WorkerHealth.HEALTHY,
                    worktree_path=str(self._worktrees_dir / f"worker-{worker_id}"),
                )
            )

    def _evaluate_pipeline_state(self, stories: list[Story]) -> PipelineState:
        if not stories:
            return PipelineState.IDLE
        if all(story.state in _TERMINAL_STORY_STATES for story in stories):
            if any(story.state == StoryState.FAILED for story in stories) and not any(
                story.state == StoryState.DONE for story in stories
            ):
                return PipelineState.FAILED
            return PipelineState.COMPLETE
        if self._stories_in_active_healing(stories):
            return PipelineState.HEALING
        if any(story.state in _ACTIVE_STORY_STATES for story in stories):
            return PipelineState.RUNNING
        if any(story.state == StoryState.QUEUED for story in stories):
            return PipelineState.RUNNING
        if any(story.state == StoryState.BLOCKED for story in stories):
            return PipelineState.RUNNING
        return PipelineState.RUNNING

    def _stories_in_active_healing(self, stories: list[Story]) -> bool:
        from ralph.common.models import HealingAttempt

        attempts_by_story: dict[int, list[HealingAttempt]] = {}
        for attempt in self._store.list_healing_attempts():
            attempts_by_story.setdefault(attempt.story_id, []).append(attempt)

        for story in stories:
            if story.state in _TERMINAL_STORY_STATES:
                continue
            attempts = attempts_by_story.get(story.id)
            if not attempts:
                continue
            if attempts[-1].reason == "self-healed":
                continue
            return True
        return False
