//! End-to-end integration tests: spawn fake-claude → collect output → parse result.
//!
//! Tests the full pipeline from process execution through output parsing,
//! verifying that `parse_claude_output` correctly handles each fake-claude mode.

use std::process::Stdio;

use ralph_worker::output::{ClaudeResult, parse_claude_output};
use ralph_worker::process::ClaudeOutput;
use rstest::*;
use tokio::process::Command;

use super::fake_claude_bin;

/// Helper: spawn fake-claude in a given mode and collect output as `ClaudeOutput`.
async fn spawn_and_collect(mode: &str) -> ClaudeOutput {
    let output = Command::new(fake_claude_bin())
        .env("FAKE_CLAUDE_MODE", mode)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .await
        .expect("failed to execute fake-claude");

    ClaudeOutput {
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).to_string(),
        exit_code: output.status.code().unwrap_or(-1),
    }
}

// ---------------------------------------------------------------------------
// Success → ClaudeResult::Success
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn e2e_success_parses_to_success_result() {
    let output = spawn_and_collect("success").await;
    let result = parse_claude_output(&output);

    match result {
        ClaudeResult::Success {
            result,
            session_id,
            cost_usd,
            duration_ms,
            num_turns,
        } => {
            assert!(!result.is_empty(), "result text should not be empty");
            assert!(session_id.is_some(), "should have session_id");
            assert!(cost_usd.is_some(), "should have cost_usd");
            assert!(duration_ms.is_some(), "should have duration_ms");
            assert!(num_turns.is_some(), "should have num_turns");
        }
        other => panic!("Expected ClaudeResult::Success, got {other:?}"),
    }
}

#[rstest]
#[tokio::test]
async fn e2e_success_has_correct_field_values() {
    let output = spawn_and_collect("success").await;
    let result = parse_claude_output(&output);

    match result {
        ClaudeResult::Success {
            session_id,
            cost_usd,
            num_turns,
            ..
        } => {
            assert_eq!(session_id, Some("fake-session-001".to_string()));
            assert_eq!(cost_usd, Some(0.05));
            assert_eq!(num_turns, Some(3));
        }
        other => panic!("Expected ClaudeResult::Success, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Failure → ClaudeResult::Failure
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn e2e_failure_parses_to_failure_result() {
    let output = spawn_and_collect("failure").await;
    let result = parse_claude_output(&output);

    match result {
        ClaudeResult::Failure { error, subtype } => {
            assert!(!error.is_empty(), "error message should not be empty");
            assert_eq!(
                subtype,
                Some("error_max_turns".to_string()),
                "should report error_max_turns subtype"
            );
        }
        other => panic!("Expected ClaudeResult::Failure, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Crash → ClaudeResult::Failure (empty stdout, stderr only)
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn e2e_crash_parses_to_failure_result() {
    let output = spawn_and_collect("crash").await;
    let result = parse_claude_output(&output);

    match result {
        ClaudeResult::Failure { error, subtype } => {
            assert!(
                error.contains("Segmentation fault"),
                "should capture stderr as error, got: {error}"
            );
            assert_eq!(subtype, None, "crash has no subtype");
        }
        other => panic!("Expected ClaudeResult::Failure, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Malformed → ClaudeResult::ParseError
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn e2e_malformed_parses_to_parse_error() {
    let output = spawn_and_collect("malformed").await;
    let result = parse_claude_output(&output);

    match result {
        ClaudeResult::ParseError { reason, raw_output } => {
            assert!(!reason.is_empty(), "parse error reason should not be empty");
            assert!(
                !raw_output.is_empty(),
                "raw_output should contain the malformed JSON"
            );
        }
        other => panic!("Expected ClaudeResult::ParseError, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Partial → ClaudeResult::ParseError (truncated JSON)
// ---------------------------------------------------------------------------

#[rstest]
#[tokio::test]
async fn e2e_partial_parses_to_parse_error_or_failure() {
    let output = spawn_and_collect("partial").await;
    let result = parse_claude_output(&output);

    // Partial mode exits 1 with truncated JSON. If stdout is empty after trim,
    // parse_claude_output returns Failure (stderr-based). Otherwise ParseError.
    match result {
        ClaudeResult::ParseError { .. } | ClaudeResult::Failure { .. } => {
            // Both are acceptable — partial output can be interpreted either way
        }
        other => panic!("Expected ClaudeResult::ParseError or Failure, got {other:?}"),
    }
}
