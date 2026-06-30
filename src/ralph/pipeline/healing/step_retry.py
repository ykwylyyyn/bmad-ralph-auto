from __future__ import annotations

from dataclasses import dataclass
import logging

from ralph.common.db.store import StateStore
from ralph.common.models import HealingAttempt, HealingLayer, StoryState

from .types import HealingOutcome, HealingOutcomeKind

logger = logging.getLogger(__name__)

SELF_HEALED_REASON = "self-healed"


@dataclass(frozen=True, slots=True)
class StepFailure:
    story_id: int
    worker_id: int
    reason: str


class Layer1StepRetry:
    """Layer 1 self-healing: automatic step retry on the same worker."""

    def __init__(self, store: StateStore, *, retry_limit: int = 3) -> None:
        if retry_limit < 1:
            raise ValueError("retry_limit must be positive")
        self._store = store
        self._retry_limit = retry_limit

    @property
    def retry_limit(self) -> int:
        return self._retry_limit

    def handle_step_failure(self, failure: StepFailure) -> HealingOutcome:
        prior_attempts = self._store.count_healing_attempts(
            failure.story_id,
            HealingLayer.STEP_RETRY,
        )
        next_attempt = prior_attempts + 1

        if next_attempt > self._retry_limit:
            return HealingOutcome(
                kind=HealingOutcomeKind.ESCALATE_LAYER2,
                story_id=failure.story_id,
                worker_id=failure.worker_id,
                attempt=prior_attempts,
                reason=failure.reason,
            )

        attempt = HealingAttempt(
            story_id=failure.story_id,
            layer=HealingLayer.STEP_RETRY,
            attempt=next_attempt,
            reason=failure.reason,
        )
        self._store.record_healing_attempt(attempt)
        self._store.set_story_state(failure.story_id, StoryState.IN_PROGRESS)
        self._log_healing_activated(failure.story_id, next_attempt)

        return HealingOutcome(
            kind=HealingOutcomeKind.RETRY,
            story_id=failure.story_id,
            worker_id=failure.worker_id,
            attempt=next_attempt,
            reason=failure.reason,
        )

    def handle_retry_success(self, story_id: int, worker_id: int) -> HealingOutcome:
        prior_attempts = self._store.count_healing_attempts(story_id, HealingLayer.STEP_RETRY)
        if prior_attempts == 0:
            return HealingOutcome(
                kind=HealingOutcomeKind.SELF_HEALED,
                story_id=story_id,
                worker_id=worker_id,
                attempt=None,
                reason=None,
            )

        self._store.record_healing_attempt(
            HealingAttempt(
                story_id=story_id,
                layer=HealingLayer.STEP_RETRY,
                attempt=prior_attempts,
                reason=SELF_HEALED_REASON,
            )
        )
        return HealingOutcome(
            kind=HealingOutcomeKind.SELF_HEALED,
            story_id=story_id,
            worker_id=worker_id,
            attempt=prior_attempts,
            reason=SELF_HEALED_REASON,
        )

    def _log_healing_activated(self, story_id: int, attempt: int) -> None:
        logger.warning(
            "healing activated",
            extra={
                "story_id": story_id,
                "attempt": attempt,
                "layer": HealingLayer.STEP_RETRY.value,
            },
        )
