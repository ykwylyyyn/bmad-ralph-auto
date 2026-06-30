from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealingOutcomeKind(StrEnum):
    RETRY = "retry"
    ESCALATE_LAYER2 = "escalate_layer2"
    SELF_HEALED = "self_healed"


@dataclass(frozen=True, slots=True)
class HealingOutcome:
    kind: HealingOutcomeKind
    story_id: int
    worker_id: int
    attempt: int | None = None
    reason: str | None = None
