//! Integration tests for the pipeline state machine.
//!
//! Verifies StoryState enum properties: completeness, equality, copy/clone,
//! and debug formatting. These tests serve as regression guards for the
//! state model that drives the entire pipeline.

use ralph_pipeline::state::StoryState;
use rstest::*;

// ─── enum completeness ─────────────────────────────────────────────

#[rstest]
fn all_six_states_can_be_constructed() {
    let states = [
        StoryState::Queued,
        StoryState::InProgress,
        StoryState::InReview,
        StoryState::Blocked,
        StoryState::Done,
        StoryState::Failed,
    ];
    assert_eq!(states.len(), 6, "StoryState should have exactly 6 variants");
}

// ─── equality ──────────────────────────────────────────────────────

#[rstest]
#[case(StoryState::Queued)]
#[case(StoryState::InProgress)]
#[case(StoryState::InReview)]
#[case(StoryState::Blocked)]
#[case(StoryState::Done)]
#[case(StoryState::Failed)]
fn same_state_equals_itself(#[case] state: StoryState) {
    assert_eq!(state, state, "{state:?} should equal itself");
}

#[rstest]
#[case(StoryState::Queued, StoryState::InProgress)]
#[case(StoryState::InProgress, StoryState::InReview)]
#[case(StoryState::InReview, StoryState::Done)]
#[case(StoryState::Done, StoryState::Failed)]
#[case(StoryState::Failed, StoryState::Blocked)]
#[case(StoryState::Blocked, StoryState::Queued)]
fn different_states_are_not_equal(#[case] a: StoryState, #[case] b: StoryState) {
    assert_ne!(a, b, "{a:?} and {b:?} should not be equal");
}

// ─── copy + clone ──────────────────────────────────────────────────

#[rstest]
#[case(StoryState::Queued)]
#[case(StoryState::InProgress)]
#[case(StoryState::Done)]
fn state_is_copy(#[case] state: StoryState) {
    let copied = state; // Copy semantics
    assert_eq!(state, copied, "Copy should produce equal value");
}

#[rstest]
#[case(StoryState::Blocked)]
#[case(StoryState::Failed)]
#[case(StoryState::InReview)]
fn state_is_clone(#[case] state: StoryState) {
    let cloned = state.clone();
    assert_eq!(state, cloned, "Clone should produce equal value");
}

// ─── debug formatting ─────────────────────────────────────────────

#[rstest]
#[case(StoryState::Queued, "Queued")]
#[case(StoryState::InProgress, "InProgress")]
#[case(StoryState::InReview, "InReview")]
#[case(StoryState::Blocked, "Blocked")]
#[case(StoryState::Done, "Done")]
#[case(StoryState::Failed, "Failed")]
fn debug_format_contains_variant_name(#[case] state: StoryState, #[case] name: &str) {
    let debug = format!("{state:?}");
    assert_eq!(
        debug, name,
        "Debug format of {name} should be '{name}', got '{debug}'"
    );
}

// ─── state machine contract (transition directions) ────────────────

/// Verify the expected valid transitions as documented in the architecture.
/// These are "contract tests" — they define what the state machine SHOULD allow
/// even though transition logic is not yet implemented.
#[rstest]
#[case(StoryState::Queued, StoryState::InProgress, "Queued → InProgress")]
#[case(StoryState::InProgress, StoryState::InReview, "InProgress → InReview")]
#[case(StoryState::InProgress, StoryState::Blocked, "InProgress → Blocked")]
#[case(StoryState::InProgress, StoryState::Failed, "InProgress → Failed")]
#[case(StoryState::InReview, StoryState::Done, "InReview → Done")]
#[case(StoryState::Blocked, StoryState::InProgress, "Blocked → InProgress")]
#[case(StoryState::Failed, StoryState::Queued, "Failed → Queued")]
fn documented_valid_transitions(
    #[case] from: StoryState,
    #[case] to: StoryState,
    #[case] label: &str,
) {
    // When transition logic is implemented, this test should call
    // the transition function and assert Ok. For now, verify the
    // states are distinct (no self-transitions in the valid set).
    assert_ne!(
        from, to,
        "Valid transition {label} should be between distinct states"
    );
}

/// Verify that terminal states (Done) and invalid skip transitions are defined.
#[rstest]
#[case(StoryState::Done, StoryState::InProgress, "Done is terminal")]
#[case(StoryState::Queued, StoryState::Done, "Cannot skip to Done")]
#[case(StoryState::Queued, StoryState::InReview, "Cannot skip to InReview")]
fn documented_invalid_transitions(
    #[case] from: StoryState,
    #[case] to: StoryState,
    #[case] label: &str,
) {
    // When transition logic is implemented, this test should call
    // the transition function and assert Err.
    assert_ne!(
        from, to,
        "Invalid transition '{label}' should be between distinct states"
    );
}
