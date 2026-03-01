//! Unit tests for pipeline state machine demonstrating rstest patterns.

#[cfg(test)]
mod tests {
    use rstest::*;
    use crate::state::StoryState;

    // ─── parametrized: valid state transitions ────────────────────

    #[rstest]
    #[case(StoryState::Queued, StoryState::InProgress)]
    #[case(StoryState::InProgress, StoryState::InReview)]
    #[case(StoryState::InProgress, StoryState::Blocked)]
    #[case(StoryState::InProgress, StoryState::Failed)]
    #[case(StoryState::InReview, StoryState::Done)]
    #[case(StoryState::Blocked, StoryState::InProgress)]
    #[case(StoryState::Failed, StoryState::Queued)]
    fn valid_transition(#[case] from: StoryState, #[case] to: StoryState) {
        // Once the transition logic is implemented, this will validate it.
        // For now, assert the states are different (placeholder).
        assert_ne!(from, to);
    }

    // ─── parametrized: invalid state transitions ──────────────────

    #[rstest]
    #[case(StoryState::Done, StoryState::InProgress)]
    #[case(StoryState::Queued, StoryState::Done)]
    #[case(StoryState::Queued, StoryState::InReview)]
    fn invalid_transition(#[case] from: StoryState, #[case] to: StoryState) {
        // Once transition logic is implemented, assert these return Err.
        assert_ne!(from, to);
    }
}
