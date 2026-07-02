from __future__ import annotations

from ralph.common.models import StoryState

VALID_TRANSITIONS = {
    (StoryState.QUEUED, StoryState.IN_PROGRESS),
    (StoryState.IN_PROGRESS, StoryState.IN_REVIEW),
    (StoryState.IN_PROGRESS, StoryState.VERIFYING),
    (StoryState.IN_PROGRESS, StoryState.BLOCKED),
    (StoryState.IN_PROGRESS, StoryState.FAILED),
    (StoryState.IN_PROGRESS, StoryState.QUEUED),
    (StoryState.VERIFYING, StoryState.DONE),
    (StoryState.VERIFYING, StoryState.FAILED),
    (StoryState.VERIFYING, StoryState.QUEUED),
    (StoryState.IN_REVIEW, StoryState.DONE),
    (StoryState.BLOCKED, StoryState.IN_PROGRESS),
    (StoryState.FAILED, StoryState.QUEUED),
}


def is_valid_transition(from_state: StoryState, to_state: StoryState) -> bool:
    return (from_state, to_state) in VALID_TRANSITIONS
