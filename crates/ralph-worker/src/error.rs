use std::path::PathBuf;

/// Errors specific to the worker process management layer.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("failed to spawn Claude process in {worktree}: {reason}")]
    ProcessSpawnFailed { worktree: PathBuf, reason: String },

    #[error("Claude process timed out after {timeout_secs}s")]
    ProcessTimeout { timeout_secs: u64 },

    #[error("failed to kill Claude process (pid {pid:?}): {reason}")]
    KillFailed { pid: Option<u32>, reason: String },

    #[error("failed to parse Claude output: {reason}")]
    OutputParseFailed { reason: String },

    #[error("Claude process exited with code {exit_code}: {stderr}")]
    ProcessFailed { exit_code: i32, stderr: String },

    #[error(transparent)]
    Io(#[from] std::io::Error),
}
