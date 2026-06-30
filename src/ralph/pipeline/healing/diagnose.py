from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import logging

from ralph.common.db.store import StateStore
from ralph.common.models import DiagnosticReport, HealingAttempt, HealingLayer, Story

from .types import HealingOutcome, HealingOutcomeKind
from .worker_restart import SELF_HEALED_REASON

logger = logging.getLogger(__name__)

_DIAGNOSE_REASON = "diagnose flow triggered"


@dataclass(frozen=True, slots=True)
class DiagnoseRequest:
    story_id: int
    worker_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class StoryDiagnoseContext:
    acceptance_criteria: list[str] = field(default_factory=list)
    log_excerpt: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DiagnosticAnalysis:
    root_cause: str
    recommendation: str
    suggested_fix: str
    failure_patterns: list[str]
    log_signals: list[str]
    spec_notes: list[str]


class FailureAnalyzer:
    """Examines healing history, worker logs, and story specification."""

    def analyze(
        self,
        story: Story,
        healing_attempts: list[HealingAttempt],
        *,
        context: StoryDiagnoseContext,
        latest_reason: str,
    ) -> DiagnosticAnalysis:
        actionable_attempts = [
            attempt
            for attempt in healing_attempts
            if attempt.reason not in {SELF_HEALED_REASON, _DIAGNOSE_REASON}
            and not attempt.reason.startswith("old_worker_id=")
        ]
        step_retries = [item for item in healing_attempts if item.layer == HealingLayer.STEP_RETRY]
        worker_restarts = [item for item in healing_attempts if item.layer == HealingLayer.WORKER_RESTART]

        failure_patterns: list[str] = []
        if step_retries:
            failure_patterns.append(
                f"Layer 1 step retry attempted {len(step_retries)} time(s) without resolution"
            )
        if worker_restarts:
            failure_patterns.append("Layer 2 worker restart did not recover the story")
        if latest_reason:
            failure_patterns.append(f"Latest failure signal: {latest_reason}")

        reason_counts = Counter(item.reason for item in actionable_attempts if item.reason)
        dominant_reason = reason_counts.most_common(1)[0][0] if reason_counts else latest_reason

        log_signals = [
            line.strip()
            for line in context.log_excerpt
            if any(token in line.lower() for token in ("error", "fail", "exception", "timeout"))
        ]

        spec_notes: list[str] = []
        if not context.acceptance_criteria:
            spec_notes.append("Story has no acceptance criteria on record")
        else:
            spec_notes.append(
                f"Story defines {len(context.acceptance_criteria)} acceptance criteria to validate"
            )

        root_cause = (
            f"Story #{story.id} ({story.title}) exhausted all healing layers. "
            f"Dominant failure pattern: {dominant_reason or 'unknown'}."
        )
        recommendation = (
            "Review failure patterns across healing attempts, inspect worker logs, "
            "and verify story acceptance criteria before re-feeding."
        )
        suggested_fix = f"ralph retry {story.id}"

        return DiagnosticAnalysis(
            root_cause=root_cause,
            recommendation=recommendation,
            suggested_fix=suggested_fix,
            failure_patterns=failure_patterns,
            log_signals=log_signals,
            spec_notes=spec_notes,
        )


class Layer3Diagnose:
    """Layer 3 self-healing: automated diagnostic analysis before user escalation."""

    def __init__(self, store: StateStore, analyzer: FailureAnalyzer | None = None) -> None:
        self._store = store
        self._analyzer = analyzer or FailureAnalyzer()

    def handle_escalation(
        self,
        request: DiagnoseRequest,
        *,
        context: StoryDiagnoseContext | None = None,
    ) -> HealingOutcome:
        story = self._store.get_story(request.story_id)
        diagnose_context = context or StoryDiagnoseContext()
        attempt_number = self._store.count_healing_attempts(
            request.story_id,
            HealingLayer.DIAGNOSE,
        ) + 1

        self._store.record_healing_attempt(
            HealingAttempt(
                story_id=request.story_id,
                layer=HealingLayer.DIAGNOSE,
                attempt=attempt_number,
                reason=_DIAGNOSE_REASON,
            )
        )
        self._log_healing_activated(request.story_id, attempt_number)

        healing_attempts = self._store.list_healing_attempts(request.story_id)
        analysis = self._analyzer.analyze(
            story,
            healing_attempts,
            context=diagnose_context,
            latest_reason=request.reason,
        )

        report = self._store.save_diagnostic_report(
            DiagnosticReport(
                story_id=request.story_id,
                root_cause=analysis.root_cause,
                recommendation=analysis.recommendation,
                suggested_fix=analysis.suggested_fix,
                analysis={
                    "failure_patterns": analysis.failure_patterns,
                    "log_signals": analysis.log_signals,
                    "spec_notes": analysis.spec_notes,
                    "healing_layers_attempted": sorted(
                        {attempt.layer.value for attempt in healing_attempts}
                    ),
                },
            )
        )
        self._store.mark_story_exhausted(request.story_id)

        return HealingOutcome(
            kind=HealingOutcomeKind.EXHAUSTED,
            story_id=request.story_id,
            worker_id=request.worker_id,
            attempt=attempt_number,
            reason=request.reason,
            diagnostic_report_id=report.id,
        )

    def _log_healing_activated(self, story_id: int, attempt: int) -> None:
        logger.warning(
            "healing activated",
            extra={
                "story_id": story_id,
                "attempt": attempt,
                "layer": HealingLayer.DIAGNOSE.value,
            },
        )
