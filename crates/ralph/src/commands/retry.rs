use clap::Args;

/// Re-feed a story into the pipeline
#[derive(Debug, Args)]
pub struct RetryArgs {
    /// Story ID to retry
    pub story_id: u32,
}
