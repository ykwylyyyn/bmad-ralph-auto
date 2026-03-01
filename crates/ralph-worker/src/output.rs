use serde::Deserialize;

use crate::process::ClaudeOutput;

/// Raw JSON structure emitted by `claude -p --output-format json`.
#[derive(Debug, Deserialize)]
struct RawClaudeResult {
    #[serde(rename = "type")]
    _result_type: String,
    subtype: Option<String>,
    result: Option<String>,
    cost_usd: Option<f64>,
    duration_ms: Option<u64>,
    is_error: Option<bool>,
    num_turns: Option<u32>,
    session_id: Option<String>,
}

/// Parsed, validated result from a Claude CLI execution.
#[derive(Debug, Clone, PartialEq)]
pub enum ClaudeResult {
    /// Claude completed the task successfully.
    Success {
        result: String,
        session_id: Option<String>,
        cost_usd: Option<f64>,
        duration_ms: Option<u64>,
        num_turns: Option<u32>,
    },
    /// Claude reported an error or non-success outcome.
    Failure {
        error: String,
        subtype: Option<String>,
    },
    /// The raw output could not be parsed as valid Claude JSON.
    ParseError { reason: String, raw_output: String },
}

/// Parse raw Claude CLI output into a structured result.
///
/// This is a pure function — no I/O, no side effects. Test it directly
/// with fixture data; no mocks needed.
pub fn parse_claude_output(output: &ClaudeOutput) -> ClaudeResult {
    // Non-zero exit with no stdout means the process failed before
    // producing any JSON (e.g. binary not found, permission denied).
    if output.exit_code != 0 && output.stdout.trim().is_empty() {
        return ClaudeResult::Failure {
            error: output.stderr.clone(),
            subtype: None,
        };
    }

    let raw: RawClaudeResult = match serde_json::from_str(&output.stdout) {
        Ok(r) => r,
        Err(e) => {
            return ClaudeResult::ParseError {
                reason: e.to_string(),
                raw_output: output.stdout.clone(),
            };
        }
    };

    if raw.is_error.unwrap_or(false) || raw.subtype.as_deref() != Some("success") {
        ClaudeResult::Failure {
            error: raw.result.unwrap_or_default(),
            subtype: raw.subtype,
        }
    } else {
        ClaudeResult::Success {
            result: raw.result.unwrap_or_default(),
            session_id: raw.session_id,
            cost_usd: raw.cost_usd,
            duration_ms: raw.duration_ms,
            num_turns: raw.num_turns,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::*;

    #[fixture]
    fn success_output() -> ClaudeOutput {
        ClaudeOutput {
            stdout: serde_json::json!({
                "type": "result",
                "subtype": "success",
                "result": "Task completed.",
                "cost_usd": 0.05,
                "duration_ms": 5000,
                "is_error": false,
                "num_turns": 3,
                "session_id": "test-session-001",
                "total_cost_usd": 0.05
            })
            .to_string(),
            stderr: String::new(),
            exit_code: 0,
        }
    }

    #[rstest]
    fn parses_successful_output(success_output: ClaudeOutput) {
        let result = parse_claude_output(&success_output);
        match result {
            ClaudeResult::Success {
                result,
                session_id,
                cost_usd,
                duration_ms,
                num_turns,
            } => {
                assert_eq!(result, "Task completed.");
                assert_eq!(session_id, Some("test-session-001".to_string()));
                assert_eq!(cost_usd, Some(0.05));
                assert_eq!(duration_ms, Some(5000));
                assert_eq!(num_turns, Some(3));
            }
            other => panic!("Expected Success, got {other:?}"),
        }
    }

    #[rstest]
    fn parses_error_output() {
        let output = ClaudeOutput {
            stdout: serde_json::json!({
                "type": "result",
                "subtype": "error_max_turns",
                "result": "Max turns reached.",
                "cost_usd": 0.10,
                "is_error": true,
                "num_turns": 10,
                "session_id": "test-session-002"
            })
            .to_string(),
            stderr: String::new(),
            exit_code: 1,
        };
        let result = parse_claude_output(&output);
        match result {
            ClaudeResult::Failure { error, subtype } => {
                assert_eq!(error, "Max turns reached.");
                assert_eq!(subtype, Some("error_max_turns".to_string()));
            }
            other => panic!("Expected Failure, got {other:?}"),
        }
    }

    #[rstest]
    #[case("not json at all")]
    #[case("{malformed")]
    #[case("")]
    fn parses_malformed_json(#[case] bad_json: &str) {
        let output = ClaudeOutput {
            stdout: bad_json.to_string(),
            stderr: String::new(),
            exit_code: 0,
        };
        let result = parse_claude_output(&output);
        assert!(
            matches!(result, ClaudeResult::ParseError { .. }),
            "Expected ParseError for input {bad_json:?}, got {result:?}"
        );
    }

    #[rstest]
    fn parses_empty_stdout_with_stderr() {
        let output = ClaudeOutput {
            stdout: String::new(),
            stderr: "claude: command not found".to_string(),
            exit_code: 127,
        };
        let result = parse_claude_output(&output);
        match result {
            ClaudeResult::Failure { error, subtype } => {
                assert_eq!(error, "claude: command not found");
                assert_eq!(subtype, None);
            }
            other => panic!("Expected Failure, got {other:?}"),
        }
    }

    #[rstest]
    fn success_with_missing_optional_fields() {
        let output = ClaudeOutput {
            stdout: serde_json::json!({
                "type": "result",
                "subtype": "success",
                "result": "Done."
            })
            .to_string(),
            stderr: String::new(),
            exit_code: 0,
        };
        let result = parse_claude_output(&output);
        match result {
            ClaudeResult::Success {
                result,
                session_id,
                cost_usd,
                duration_ms,
                num_turns,
            } => {
                assert_eq!(result, "Done.");
                assert_eq!(session_id, None);
                assert_eq!(cost_usd, None);
                assert_eq!(duration_ms, None);
                assert_eq!(num_turns, None);
            }
            other => panic!("Expected Success, got {other:?}"),
        }
    }

    #[rstest]
    fn is_error_true_overrides_success_subtype() {
        let output = ClaudeOutput {
            stdout: serde_json::json!({
                "type": "result",
                "subtype": "success",
                "result": "Weird edge case.",
                "is_error": true
            })
            .to_string(),
            stderr: String::new(),
            exit_code: 0,
        };
        let result = parse_claude_output(&output);
        assert!(
            matches!(result, ClaudeResult::Failure { .. }),
            "is_error=true should produce Failure even with subtype=success"
        );
    }
}
