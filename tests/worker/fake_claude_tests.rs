//! Integration tests verifying each `fake-claude` mode produces expected output.
//!
//! These tests validate the test infrastructure itself — ensuring the fake-claude
//! binary behaves correctly so it can be relied upon in higher-level tests.

use std::process::Stdio;
use std::time::Instant;

use rstest::*;
use tokio::process::Command;

use super::fake_claude_bin;

/// Helper: run fake-claude with a given mode and optional env overrides.
async fn run_fake_claude(mode: &str) -> std::process::Output {
    Command::new(fake_claude_bin())
        .env("FAKE_CLAUDE_MODE", mode)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await
        .expect("failed to execute fake-claude")
}

// ---------------------------------------------------------------------------
// Success mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn success_mode_exits_zero() {
    let output = run_fake_claude("success").await;
    assert!(output.status.success(), "success mode should exit 0");
}

#[rstest]
#[tokio::test]
async fn success_mode_outputs_valid_json() {
    let output = run_fake_claude("success").await;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(stdout.trim()).expect("success mode should produce valid JSON");
    assert_eq!(parsed["type"], "result");
    assert_eq!(parsed["subtype"], "success");
}

#[rstest]
#[tokio::test]
async fn success_mode_json_has_expected_fields() {
    let output = run_fake_claude("success").await;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let parsed: serde_json::Value = serde_json::from_str(stdout.trim()).unwrap();

    assert!(parsed["result"].is_string(), "should have result field");
    assert!(parsed["cost_usd"].is_f64(), "should have cost_usd field");
    assert!(
        parsed["duration_ms"].is_u64(),
        "should have duration_ms field"
    );
    assert_eq!(parsed["is_error"], false, "success should not be error");
    assert!(parsed["num_turns"].is_u64(), "should have num_turns field");
    assert!(
        parsed["session_id"].is_string(),
        "should have session_id field"
    );
}

// ---------------------------------------------------------------------------
// Failure mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn failure_mode_exits_nonzero() {
    let output = run_fake_claude("failure").await;
    assert!(
        !output.status.success(),
        "failure mode should exit non-zero"
    );
}

#[rstest]
#[tokio::test]
async fn failure_mode_reports_is_error_true() {
    let output = run_fake_claude("failure").await;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let parsed: serde_json::Value = serde_json::from_str(stdout.trim()).unwrap();
    assert_eq!(
        parsed["is_error"], true,
        "failure mode should set is_error=true"
    );
    assert_eq!(
        parsed["subtype"], "error_max_turns",
        "failure mode should set subtype=error_max_turns"
    );
}

// ---------------------------------------------------------------------------
// Crash mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn crash_mode_exits_139() {
    let output = run_fake_claude("crash").await;
    assert_eq!(
        output.status.code(),
        Some(139),
        "crash mode should exit with code 139 (SIGSEGV)"
    );
}

#[rstest]
#[tokio::test]
async fn crash_mode_writes_to_stderr() {
    let output = run_fake_claude("crash").await;
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Segmentation fault"),
        "crash mode should write segfault to stderr, got: {stderr}"
    );
}

// ---------------------------------------------------------------------------
// Malformed mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn malformed_mode_outputs_invalid_json() {
    let output = run_fake_claude("malformed").await;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let result = serde_json::from_str::<serde_json::Value>(stdout.trim());
    assert!(
        result.is_err(),
        "malformed mode should produce unparseable JSON, got: {stdout}"
    );
}

// ---------------------------------------------------------------------------
// Partial mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn partial_mode_exits_nonzero() {
    let output = run_fake_claude("partial").await;
    assert!(
        !output.status.success(),
        "partial mode should exit non-zero"
    );
}

#[rstest]
#[tokio::test]
async fn partial_mode_outputs_truncated_json() {
    let output = run_fake_claude("partial").await;
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.starts_with("{\"type\""),
        "partial mode should start with JSON, got: {stdout}"
    );
    let result = serde_json::from_str::<serde_json::Value>(&stdout);
    assert!(
        result.is_err(),
        "partial mode should produce incomplete JSON"
    );
}

// ---------------------------------------------------------------------------
// Delay mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn delay_mode_respects_timing() {
    let start = Instant::now();
    let _output = Command::new(fake_claude_bin())
        .env("FAKE_CLAUDE_MODE", "success")
        .env("FAKE_CLAUDE_DELAY_MS", "200")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await
        .expect("failed to execute fake-claude with delay");
    let elapsed = start.elapsed();

    assert!(
        elapsed.as_millis() >= 150,
        "with 200ms delay, should take at least 150ms, took {}ms",
        elapsed.as_millis()
    );
}

// ---------------------------------------------------------------------------
// Exit code override
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn exit_code_override_works() {
    let output = Command::new(fake_claude_bin())
        .env("FAKE_CLAUDE_MODE", "success")
        .env("FAKE_CLAUDE_EXIT_CODE", "42")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await
        .expect("failed to execute fake-claude with exit code override");

    assert_eq!(
        output.status.code(),
        Some(42),
        "exit code override should produce exit code 42"
    );
}

// ---------------------------------------------------------------------------
// Unknown mode
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn unknown_mode_exits_with_error() {
    let output = run_fake_claude("nonexistent_mode").await;
    assert_eq!(
        output.status.code(),
        Some(2),
        "unknown mode should exit with code 2"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Unknown FAKE_CLAUDE_MODE"),
        "should report unknown mode in stderr, got: {stderr}"
    );
}

// ---------------------------------------------------------------------------
// Kill hanging process
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn kill_hanging_process_terminates() {
    let mut child = Command::new(fake_claude_bin())
        .env("FAKE_CLAUDE_MODE", "hang")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("failed to spawn fake-claude in hang mode");

    // Give it a moment to start
    tokio::time::sleep(std::time::Duration::from_millis(50)).await;

    // Kill it
    child
        .kill()
        .await
        .expect("should be able to kill hanging process");
    let status = child
        .wait()
        .await
        .expect("should be able to wait after kill");
    assert!(
        !status.success(),
        "killed process should have non-success exit status"
    );
}
