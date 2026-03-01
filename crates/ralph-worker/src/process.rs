use std::path::Path;

use async_trait::async_trait;
use tokio::sync::mpsc;

use crate::error::Error;

/// A single line of streaming output from the Claude CLI.
#[derive(Debug, Clone)]
pub struct OutputLine {
    pub content: String,
    pub stream: OutputStream,
}

/// Which output stream a line came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputStream {
    Stdout,
    Stderr,
}

/// Final collected output from a completed Claude CLI process.
#[derive(Debug, Clone)]
pub struct ClaudeOutput {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

/// Factory trait for creating Claude Code sessions.
///
/// Maps to the "spawn" phase of the cattle model: create a new disposable
/// worker process. Equivalent to `Command` in the tokio process model.
#[cfg_attr(any(test, feature = "mock"), mockall::automock)]
#[async_trait]
pub trait ClaudeProcess: Send + Sync {
    /// Spawn a new Claude Code CLI process in the given worktree.
    ///
    /// If `output_tx` is provided, streaming output lines are sent to it
    /// as they arrive (for live monitoring / TUI display).
    async fn spawn(
        &self,
        worktree_path: &Path,
        prompt: &str,
        output_tx: Option<mpsc::Sender<OutputLine>>,
    ) -> Result<Box<dyn ClaudeSessionHandle>, Error>;
}

/// Handle to a running Claude Code session.
///
/// Maps to the "monitor / kill / respawn" phase of the cattle model.
/// Equivalent to `Child` in the tokio process model. Disposable by design.
#[cfg_attr(any(test, feature = "mock"), mockall::automock)]
#[async_trait]
pub trait ClaudeSessionHandle: Send + Sync {
    /// Check whether the process is still running.
    async fn is_running(&self) -> bool;

    /// Wait for the process to complete and collect its output.
    async fn wait(&mut self) -> Result<ClaudeOutput, Error>;

    /// Kill the process immediately.
    async fn kill(&mut self) -> Result<(), Error>;

    /// Return the OS process ID, if known.
    fn pid(&self) -> Option<u32>;
}
