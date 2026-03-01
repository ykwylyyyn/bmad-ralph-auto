//! Fake Claude CLI binary for integration testing.
//!
//! Controlled entirely via environment variables:
//!
//! - `FAKE_CLAUDE_MODE`: Determines behavior (default: "success")
//!   - `success`   — output a valid success JSON and exit 0
//!   - `failure`   — output a valid error JSON and exit non-zero
//!   - `hang`      — block forever (for timeout / kill testing)
//!   - `crash`     — print to stderr and exit 139 (SIGSEGV)
//!   - `malformed` — output invalid JSON
//!   - `slow`      — output valid JSON one byte at a time
//!   - `partial`   — output truncated JSON then exit 1
//!
//! - `FAKE_CLAUDE_DELAY_MS`: Sleep this many ms before producing output (default: 0)
//! - `FAKE_CLAUDE_EXIT_CODE`: Override exit code (default: mode-dependent)

use std::env;
use std::io::{self, Write};
use std::process;
use std::thread;
use std::time::Duration;

fn main() {
    let mode = env::var("FAKE_CLAUDE_MODE").unwrap_or_else(|_| "success".to_string());
    let delay_ms: u64 = env::var("FAKE_CLAUDE_DELAY_MS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    let exit_code_override: Option<i32> = env::var("FAKE_CLAUDE_EXIT_CODE")
        .ok()
        .and_then(|v| v.parse().ok());

    if delay_ms > 0 {
        thread::sleep(Duration::from_millis(delay_ms));
    }

    match mode.as_str() {
        "success" => {
            let result = serde_json::json!({
                "type": "result",
                "subtype": "success",
                "result": "Task completed successfully.\n\nI've made the requested changes.",
                "cost_usd": 0.05,
                "duration_ms": 5000,
                "duration_api_ms": 4500,
                "is_error": false,
                "num_turns": 3,
                "session_id": "fake-session-001",
                "total_cost_usd": 0.05
            });
            println!("{result}");
            process::exit(exit_code_override.unwrap_or(0));
        }
        "failure" => {
            let result = serde_json::json!({
                "type": "result",
                "subtype": "error_max_turns",
                "result": "Max turns reached without completing the task.",
                "cost_usd": 0.10,
                "duration_ms": 30000,
                "is_error": true,
                "num_turns": 10,
                "session_id": "fake-session-002",
                "total_cost_usd": 0.10
            });
            println!("{result}");
            process::exit(exit_code_override.unwrap_or(1));
        }
        "hang" => loop {
            thread::sleep(Duration::from_secs(3600));
        },
        "crash" => {
            eprintln!("Segmentation fault (core dumped)");
            process::exit(exit_code_override.unwrap_or(139));
        }
        "malformed" => {
            println!("{{\"type\": \"result\", \"subtype\": \"success\", INVALID JSON");
            process::exit(exit_code_override.unwrap_or(0));
        }
        "slow" => {
            let result = serde_json::json!({
                "type": "result",
                "subtype": "success",
                "result": "Completed after slow execution.",
                "cost_usd": 0.02,
                "duration_ms": 10000,
                "is_error": false,
                "num_turns": 1,
                "session_id": "fake-session-003",
                "total_cost_usd": 0.02
            });
            let output = format!("{result}\n");
            for byte in output.bytes() {
                io::stdout().write_all(&[byte]).ok();
                io::stdout().flush().ok();
                thread::sleep(Duration::from_millis(10));
            }
            process::exit(exit_code_override.unwrap_or(0));
        }
        "partial" => {
            print!("{{\"type\": \"result\", \"sub");
            io::stdout().flush().ok();
            process::exit(exit_code_override.unwrap_or(1));
        }
        unknown => {
            eprintln!("Unknown FAKE_CLAUDE_MODE: {unknown}");
            process::exit(2);
        }
    }
}
