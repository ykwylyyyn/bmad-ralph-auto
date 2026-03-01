use clap::Args;

/// Generate diagnostic report for a story
#[derive(Debug, Args)]
pub struct DiagnoseArgs {
    /// Story ID to diagnose
    pub story_id: u32,
}
