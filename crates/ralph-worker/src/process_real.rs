use std::path::Path;
use std::process::Stdio;

use async_trait::async_trait;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::mpsc;
use tracing::{debug, trace};

use crate::error::Error;
use crate::process::{ClaudeOutput, ClaudeProcess, ClaudeSessionHandle, OutputLine, OutputStream};

/// Production implementation that spawns real Claude CLI processes.
///
/// Uses `tokio::process::Command` with `kill_on_drop(true)` to ensure
/// child processes are cleaned up if the handle is dropped.
pub struct RealClaudeProcess {
    claude_bin: String,
}

impl RealClaudeProcess {
    /// Create a new factory that spawns the default `claude` binary.
    pub fn new() -> Self {
        Self {
            claude_bin: "claude".to_string(),
        }
    }

    /// Create a factory that spawns a specific binary (e.g. a fake CLI for testing).
    pub fn with_bin(claude_bin: impl Into<String>) -> Self {
        Self {
            claude_bin: claude_bin.into(),
        }
    }
}

impl Default for RealClaudeProcess {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ClaudeProcess for RealClaudeProcess {
    async fn spawn(
        &self,
        worktree_path: &Path,
        prompt: &str,
        output_tx: Option<mpsc::Sender<OutputLine>>,
    ) -> Result<Box<dyn ClaudeSessionHandle>, Error> {
        debug!(
            worktree = %worktree_path.display(),
            prompt_len = prompt.len(),
            bin = %self.claude_bin,
            "spawning Claude process"
        );

        let mut child = Command::new(&self.claude_bin)
            .arg("-p")
            .arg(prompt)
            .arg("--output-format")
            .arg("json")
            .current_dir(worktree_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true)
            .spawn()
            .map_err(|e| Error::ProcessSpawnFailed {
                worktree: worktree_path.to_path_buf(),
                reason: e.to_string(),
            })?;

        let pid = child.id();

        let stdout = child.stdout.take();
        let stderr = child.stderr.take();

        let stdout_handle = tokio::spawn({
            let tx = output_tx.clone();
            async move {
                let mut lines = Vec::new();
                if let Some(stdout) = stdout {
                    let mut reader = BufReader::new(stdout).lines();
                    while let Ok(Some(line)) = reader.next_line().await {
                        trace!(line = %line, "stdout");
                        if let Some(ref tx) = tx {
                            let _ = tx
                                .send(OutputLine {
                                    content: line.clone(),
                                    stream: OutputStream::Stdout,
                                })
                                .await;
                        }
                        lines.push(line);
                    }
                }
                lines.join("\n")
            }
        });

        let stderr_handle = tokio::spawn({
            let tx = output_tx;
            async move {
                let mut lines = Vec::new();
                if let Some(stderr) = stderr {
                    let mut reader = BufReader::new(stderr).lines();
                    while let Ok(Some(line)) = reader.next_line().await {
                        trace!(line = %line, "stderr");
                        if let Some(ref tx) = tx {
                            let _ = tx
                                .send(OutputLine {
                                    content: line.clone(),
                                    stream: OutputStream::Stderr,
                                })
                                .await;
                        }
                        lines.push(line);
                    }
                }
                lines.join("\n")
            }
        });

        Ok(Box::new(RealClaudeSession {
            child,
            pid,
            stdout_handle: Some(stdout_handle),
            stderr_handle: Some(stderr_handle),
            finished: false,
        }))
    }
}

/// A live Claude CLI session backed by a real OS process.
struct RealClaudeSession {
    child: Child,
    pid: Option<u32>,
    stdout_handle: Option<tokio::task::JoinHandle<String>>,
    stderr_handle: Option<tokio::task::JoinHandle<String>>,
    finished: bool,
}

#[async_trait]
impl ClaudeSessionHandle for RealClaudeSession {
    async fn is_running(&self) -> bool {
        !self.finished
    }

    async fn wait(&mut self) -> Result<ClaudeOutput, Error> {
        let status = self.child.wait().await?;
        self.finished = true;

        let stdout = if let Some(handle) = self.stdout_handle.take() {
            handle.await.unwrap_or_default()
        } else {
            String::new()
        };

        let stderr = if let Some(handle) = self.stderr_handle.take() {
            handle.await.unwrap_or_default()
        } else {
            String::new()
        };

        Ok(ClaudeOutput {
            stdout,
            stderr,
            exit_code: status.code().unwrap_or(-1),
        })
    }

    async fn kill(&mut self) -> Result<(), Error> {
        self.child.kill().await.map_err(|e| Error::KillFailed {
            pid: self.pid,
            reason: e.to_string(),
        })?;
        self.finished = true;
        Ok(())
    }

    fn pid(&self) -> Option<u32> {
        self.pid
    }
}
