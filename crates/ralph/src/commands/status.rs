use clap::Args;

/// Query pipeline status
#[derive(Debug, Args)]
pub struct StatusArgs {
    /// Show expanded detail view
    #[arg(long)]
    pub detail: bool,
}
