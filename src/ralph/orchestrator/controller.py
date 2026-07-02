from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from ralph.common.db.store import StateStore
from ralph.common.models import PipelineState, StoryState
from ralph.memory.sprint_store import SprintMemoryStore
from ralph.orchestrator.config import OrchestratorConfig
from ralph.orchestrator.feedback import BmadFeedbackWatcher, FeedbackEvent
from ralph.pipeline.engine import PipelineEngine, PipelineTickResult
from ralph.pipeline.story_cycle import StoryCycleConfig
from ralph.router.config import RouterConfig
from ralph.verifier.config import VerifierConfig


class FlowPhase(StrEnum):
  PLAN = "plan"
  EXECUTE = "execute"
  REVIEW = "review"
  REPLAN = "replan"


@dataclass(slots=True)
class OrchestratorTickResult:
  phase: FlowPhase
  pipeline: PipelineTickResult
  feedback_events: list[FeedbackEvent] = field(default_factory=list)
  auto_done_count: int = 0


class UnifiedOrchestrator:
  """Central controller unifying BMAD planning artifacts with Ralph execution."""

  def __init__(
    self,
    store: StateStore,
    *,
    project_dir: Path,
    max_workers: int,
    worktrees_dir: Path,
    logs_dir: Path | None = None,
    retry_limit: int = 3,
    verifier_config: VerifierConfig | None = None,
    story_cycle_config: StoryCycleConfig | None = None,
    router_config: RouterConfig | None = None,
    orchestrator_config: OrchestratorConfig | None = None,
    engine: PipelineEngine | None = None,
  ) -> None:
    self._store = store
    self._project_dir = project_dir.resolve()
    self._config = (orchestrator_config or OrchestratorConfig()).effective()
    self._sprint_memory = SprintMemoryStore(store)
    self._feedback = BmadFeedbackWatcher(self._project_dir)
    self._engine = engine or PipelineEngine(
      store,
      project_dir=self._project_dir,
      max_workers=max_workers,
      worktrees_dir=worktrees_dir,
      logs_dir=logs_dir,
      retry_limit=retry_limit,
      verifier_config=verifier_config,
      story_cycle_config=story_cycle_config,
      router_config=router_config,
    )

  @property
  def engine(self) -> PipelineEngine:
    return self._engine

  @property
  def sprint_memory(self) -> SprintMemoryStore:
    return self._sprint_memory

  def initialize(self) -> PipelineState:
    return self._engine.initialize()

  def tick(self) -> OrchestratorTickResult:
    pipeline_result = self._engine.tick()
    feedback_events: list[FeedbackEvent] = []
    auto_done_count = 0

    if self._config.feedback_loop:
      feedback_events = self._feedback.poll()
      for event in feedback_events:
        self._store.record_pipeline_event(
          "bmad_feedback",
          {
            "artifact_path": event.artifact_path,
            "event_type": event.event_type,
            "story_key": event.story_key,
          },
        )

    if self._config.auto_done:
      auto_done_count = self._promote_reviewed_stories()

    self._record_sprint_snapshot(pipeline_result.pipeline_state)
    phase = self._resolve_phase(pipeline_result.pipeline_state)

    return OrchestratorTickResult(
      phase=phase,
      pipeline=pipeline_result,
      feedback_events=feedback_events,
      auto_done_count=auto_done_count,
    )

  def shutdown(self) -> None:
    self._engine.shutdown()

  def status_message(self, tick: OrchestratorTickResult) -> str:
    base = self._engine.status_message(tick.pipeline)
    if tick.feedback_events:
      return f"{base}; feedback={len(tick.feedback_events)}"
    if tick.auto_done_count:
      return f"{base}; auto_done={tick.auto_done_count}"
    return base

  def _resolve_phase(self, pipeline_state: PipelineState) -> FlowPhase:
    if pipeline_state == PipelineState.HEALING:
      return FlowPhase.REPLAN
    stories = self._store.list_stories()
    if not stories:
      return FlowPhase.PLAN
    if any(story.state == StoryState.IN_REVIEW for story in stories):
      return FlowPhase.REVIEW
    if pipeline_state in {PipelineState.COMPLETE, PipelineState.IDLE}:
      return FlowPhase.PLAN
    return FlowPhase.EXECUTE

  def _promote_reviewed_stories(self) -> int:
    promoted = 0
    for story in self._store.list_stories():
      if story.state != StoryState.IN_REVIEW:
        continue
      self._store.transition_story_state(story.id, StoryState.DONE)
      promoted += 1
    return promoted

  def _record_sprint_snapshot(self, pipeline_state: PipelineState) -> None:
    stories = self._store.list_stories()
    done = sum(1 for story in stories if story.state == StoryState.DONE)
    failed = sum(1 for story in stories if story.state == StoryState.FAILED)
    self._sprint_memory.record_snapshot(
      {
        "pipeline_state": pipeline_state.value,
        "total_stories": len(stories),
        "done": done,
        "failed": failed,
      }
    )
