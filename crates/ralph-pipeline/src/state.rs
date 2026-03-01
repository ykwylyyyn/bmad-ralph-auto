/// Pipeline story states following the state machine design.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StoryState {
    Queued,
    InProgress,
    InReview,
    Blocked,
    Done,
    Failed,
}
