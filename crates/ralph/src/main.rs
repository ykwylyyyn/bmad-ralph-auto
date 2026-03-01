mod commands;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "ralph", version, about = "Autonomous SDLC pipeline runner")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Commands>,

    /// Disable color output
    #[arg(long, global = true)]
    pub no_color: bool,

    /// Suppress non-essential output
    #[arg(short, long, global = true)]
    pub quiet: bool,

    /// Show additional detail
    #[arg(short, long, global = true)]
    pub verbose: bool,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Start the Ralph daemon
    Start(commands::daemon::start::StartArgs),
    /// Stop the Ralph daemon
    Stop(commands::daemon::stop::StopArgs),
    /// Query pipeline status
    Status(commands::status::StatusArgs),
    /// Generate diagnostic report for a story
    Diagnose(commands::diagnose::DiagnoseArgs),
    /// Re-feed a story into the pipeline
    Retry(commands::retry::RetryArgs),
    /// Initialize Ralph on a project
    Init(commands::init::InitArgs),
    /// Live TUI monitoring dashboard
    Watch(commands::watch::WatchArgs),
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Some(Commands::Start(_)) => println!("start: not yet implemented"),
        Some(Commands::Stop(_)) => println!("stop: not yet implemented"),
        Some(Commands::Status(_)) => println!("status: not yet implemented"),
        Some(Commands::Diagnose(_)) => println!("diagnose: not yet implemented"),
        Some(Commands::Retry(_)) => println!("retry: not yet implemented"),
        Some(Commands::Init(_)) => println!("init: not yet implemented"),
        Some(Commands::Watch(_)) => println!("watch: not yet implemented"),
        None => {
            use clap::CommandFactory;
            Cli::command().print_help()?;
            println!();
        }
    }

    Ok(())
}
