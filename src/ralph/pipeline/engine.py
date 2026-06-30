from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ralph.common.db.store import StateStore, WorkerRecord
from ralph.common.models import PipelineState, Story, StoryState, WorkerHealth, WorkerState
from ralph.pipeline.dependency_graph import DependencyGraph
from ralph.pipeline.ingestion import build_dependency_graph
from ralph.pipeline.scheduler import StoryScheduler
from ralph.worker.errors import WorkerSpawnError
from ralph.worker.manager import WorkerCompletion, WorkerManager, story_state_for_result

_TERMINAL_STORY_STATES = {StoryState.DONE, StoryState.FAILED}


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
    completions: list[WorkerCompletion] = field(default_factory=list)
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
        worker_manager: WorkerManager | None = None,
    ) -> None:
        self._store = store
        self._project_dir = project_dir.resolve()
        self._scheduler = StoryScheduler(max_workers)
        self._worktrees_dir = worktrees_dir
        self._worker_manager = worker_manager or WorkerManager(project_dir, worktrees_dir)
        self._graph: DependencyGraph | None = None

    @property
    def worker_manager(self) -> WorkerManager:
        return self._worker_manager

    def initialize(self) -> PipelineState:
        stories = self._store.list_stories()
        if not stories:
            self._store.set_pipeline_state(PipelineState.IDLE)
            return PipelineState.IDLE

        self._graph = build_dependency_graph(stories)
        self._ensure_worker_pool()
        state = PipelineState.RUNNING
        self._store.set_pipeline_state(state)
        return state

    def shutdown(self) -> None:
        self._worker_manager.shutdown()

    def tick(self) -> PipelineTickResult:
        completions = self._worker_manager.poll_completions()
        for completion in completions:
            self._handle_completion(completion)

        stories = self._store.list_stories()
        if not stories:
            self._store.set_pipeline_state(PipelineState.IDLE)
            return PipelineTickResult(pipeline_state=PipelineState.IDLE, completions=completions)

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

            self._store.assign_story_to_worker(story.id, worker.id)
            try:
                active = self._worker_manager.spawn_for_story(worker.id, story)
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
            spawn_failures=spawn_failures,
            schedulable_count=len(snapshot.schedulable),
            active_workers=self._scheduler.active_worker_count(workers),
            completed_stories=completed,
            sprint_completed=sprint_completed,
        )

    def status_message(self, tick: PipelineTickResult) -> str:
        if tick.pipeline_state == PipelineState.COMPLETE:
            return f"pipeline complete: {tick.completed_stories} stories done"
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

    def _handle_completion(self, completion: WorkerCompletion) -> None:
        target_state = story_state_for_result(completion.result)
        story = self._store.get_story(completion.story_id)
        if story.state == StoryState.IN_PROGRESS:
            self._store.transition_story_state(completion.story_id, target_state)
        self._store.upsert_worker(
            WorkerRecord(
                id=completion.worker_id,
                state=WorkerState.IDLE,
                health=WorkerHealth.HEALTHY,
                worktree_path=str(self._worktrees_dir / f"worker-{completion.worker_id}"),
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
        if any(story.state == StoryState.IN_PROGRESS for story in stories):
            return PipelineState.RUNNING
        if any(story.state == StoryState.QUEUED for story in stories):
            return PipelineState.RUNNING
        return PipelineState.RUNNING
