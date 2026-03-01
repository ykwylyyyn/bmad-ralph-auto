//! Integration tests for `RealClaudeProcess` API using fake-claude binary.
//!
//! These tests exercise the production `RealClaudeProcess` implementation
//! end-to-end, verifying spawn, wait, pid, and streaming output work correctly.
//!
//! Note: Only the default success mode is testable through `RealClaudeProcess`
//! since env var customization is not exposed in the API.

use std::path::PathBuf;
use std::sync::Arc;

use ralph_worker::output::{ClaudeResult, parse_claude_output};
use ralph_worker::process::{ClaudeProcess, OutputStream};
use ralph_worker::process_real::RealClaudeProcess;
use rstest::*;
use tempfile::TempDir;
use tokio::sync::mpsc;

use super::fake_claude_bin;

// ─── fixtures ──────────────────────────────────────────────────────

/// Fixture: isolated temp directory as a fake worktree.
#[fixture]
fn worktree() -> (TempDir, PathBuf) {
    let dir = TempDir::new().unwrap();
    let path = dir.path().to_path_buf();
    (dir, path)
}

/// Fixture: RealClaudeProcess backed by fake-claude binary.
#[fixture]
fn process() -> RealClaudeProcess {
    RealClaudeProcess::with_bin(fake_claude_bin().to_string_lossy().to_string())
}

// ─── spawn + wait ──────────────────────────────────────────────────

#[rstest]
#[tokio::test]
async fn spawn_and_wait_returns_valid_output(
    process: RealClaudeProcess,
    worktree: (TempDir, PathBuf),
) {
    let (_guard, path) = worktree;
    let mut session = process
        .spawn(&path, "test prompt", None)
        .await
        .expect("spawn should succeed");

    let output = session.wait().await.expect("wait should succeed");
    assert_eq!(output.exit_code, 0, "fake-claude default mode exits 0");
    assert!(!output.stdout.is_empty(), "should capture stdout");
}

#[rstest]
#[tokio::test]
async fn spawn_and_wait_output_is_parseable(
    process: RealClaudeProcess,
    worktree: (TempDir, PathBuf),
) {
    let (_guard, path) = worktree;
    let mut session = process.spawn(&path, "test prompt", None).await.unwrap();
    let output = session.wait().await.unwrap();
    let result = parse_claude_output(&output);

    assert!(
        matches!(result, ClaudeResult::Success { .. }),
        "default mode should parse to Success, got {result:?}"
    );
}

// ─── pid ───────────────────────────────────────────────────────────

#[rstest]
#[tokio::test]
async fn session_has_pid_after_spawn(process: RealClaudeProcess, worktree: (TempDir, PathBuf)) {
    let (_guard, path) = worktree;
    let session = process.spawn(&path, "test prompt", None).await.unwrap();

    // pid() should return Some for a real process
    assert!(
        session.pid().is_some(),
        "spawned session should have a process ID"
    );
}

// ─── is_running ────────────────────────────────────────────────────

#[rstest]
#[tokio::test]
async fn session_not_running_after_wait(process: RealClaudeProcess, worktree: (TempDir, PathBuf)) {
    let (_guard, path) = worktree;
    let mut session = process.spawn(&path, "test prompt", None).await.unwrap();
    let _output = session.wait().await.unwrap();

    assert!(
        !session.is_running().await,
        "session should not be running after wait() completes"
    );
}

// ─── streaming output ──────────────────────────────────────────────

#[rstest]
#[tokio::test]
async fn streaming_output_received_via_channel(
    process: RealClaudeProcess,
    worktree: (TempDir, PathBuf),
) {
    let (_guard, path) = worktree;
    let (tx, mut rx) = mpsc::channel(100);

    let mut session = process.spawn(&path, "test prompt", Some(tx)).await.unwrap();

    // Wait for process to complete — this also awaits all output tasks
    let _output = session.wait().await.unwrap();

    // Collect all streamed lines
    let mut lines = Vec::new();
    while let Some(line) = rx.recv().await {
        lines.push(line);
    }

    // fake-claude success mode outputs one JSON line to stdout
    assert!(
        !lines.is_empty(),
        "should receive at least one output line via channel"
    );

    // Verify at least one stdout line
    let stdout_lines: Vec<_> = lines
        .iter()
        .filter(|l| l.stream == OutputStream::Stdout)
        .collect();
    assert!(
        !stdout_lines.is_empty(),
        "should receive at least one stdout line"
    );
    assert!(
        !stdout_lines[0].content.is_empty(),
        "stdout line content should not be empty"
    );
}

// ─── spawn failure ─────────────────────────────────────────────────

#[rstest]
#[tokio::test]
async fn spawn_nonexistent_binary_returns_error(worktree: (TempDir, PathBuf)) {
    let (_guard, path) = worktree;
    let process = RealClaudeProcess::with_bin("/nonexistent/binary/that/does/not/exist");

    let result = process.spawn(&path, "test prompt", None).await;
    assert!(
        result.is_err(),
        "spawning a nonexistent binary should return an error"
    );
}

// ─── Arc<dyn ClaudeProcess> usage ──────────────────────────────────

#[rstest]
#[tokio::test]
async fn process_works_as_arc_dyn_trait(worktree: (TempDir, PathBuf)) {
    let (_guard, path) = worktree;
    let process: Arc<dyn ClaudeProcess> = Arc::new(RealClaudeProcess::with_bin(
        fake_claude_bin().to_string_lossy().to_string(),
    ));

    let mut session = process.spawn(&path, "test prompt", None).await.unwrap();
    let output = session.wait().await.unwrap();
    assert_eq!(output.exit_code, 0);
}
