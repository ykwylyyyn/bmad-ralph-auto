//! ATDD CLI E2E tests for help output and subcommands.
//!
//! Story 1.1 / AC2: `ralph --help` shows subcommands:
//!   start, stop, status, diagnose, retry, init, watch

use assert_cmd::cargo_bin_cmd;
use predicates::prelude::*;

// ---------------------------------------------------------------------------
// Individual subcommand presence in --help
// ---------------------------------------------------------------------------

#[test]
fn ralph_help_shows_start_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("start"));
}

#[test]
fn ralph_help_shows_stop_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("stop"));
}

#[test]
fn ralph_help_shows_status_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("status"));
}

#[test]
fn ralph_help_shows_diagnose_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("diagnose"));
}

#[test]
fn ralph_help_shows_retry_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("retry"));
}

#[test]
fn ralph_help_shows_init_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("init"));
}

#[test]
fn ralph_help_shows_watch_subcommand() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("watch"));
}

// ---------------------------------------------------------------------------
// Composite check: all 7 subcommands present
// ---------------------------------------------------------------------------

#[test]
fn ralph_help_shows_all_subcommands() {
    let assert = cargo_bin_cmd!("ralph").arg("--help").assert().success();

    let stdout = String::from_utf8_lossy(&assert.get_output().stdout);

    let expected_subcommands = [
        "start", "stop", "status", "diagnose", "retry", "init", "watch",
    ];
    for subcmd in &expected_subcommands {
        assert!(
            stdout.contains(subcmd),
            "Expected subcommand '{}' not found in --help output:\n{}",
            subcmd,
            stdout,
        );
    }
}

// ---------------------------------------------------------------------------
// Error handling: invalid subcommand
// ---------------------------------------------------------------------------

#[test]
fn ralph_invalid_subcommand_shows_error() {
    cargo_bin_cmd!("ralph")
        .arg("invalid-cmd")
        .assert()
        .failure()
        .stderr(predicate::str::contains("error"));
}

// ---------------------------------------------------------------------------
// Subcommand help: `ralph start --help`
// ---------------------------------------------------------------------------

#[test]
fn ralph_start_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["start", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("start").and(predicate::str::is_empty().not()));
}
