use std::path::PathBuf;
use std::sync::Arc;

use crate::process::ClaudeProcess;

/// Represents a Claude Code worker session.
///
/// Each worker operates in an isolated git worktree and uses a
/// `ClaudeProcess` factory to spawn Claude CLI sessions.
pub struct Worker {
    pub id: u32,
    pub worktree_path: PathBuf,
    process_factory: Arc<dyn ClaudeProcess>,
}

impl Worker {
    pub fn new(id: u32, worktree_path: PathBuf, process_factory: Arc<dyn ClaudeProcess>) -> Self {
        Self {
            id,
            worktree_path,
            process_factory,
        }
    }

    /// Access the process factory (e.g. to spawn a Claude session).
    pub fn process_factory(&self) -> &dyn ClaudeProcess {
        self.process_factory.as_ref()
    }
}
