//! E2E tests for CLI subcommand execution.
//!
//! Verifies that each subcommand runs successfully and produces expected output.
//! Currently all commands are stubs, so we verify the stub messages.

use assert_cmd::cargo_bin_cmd;
use predicates::prelude::*;

// ---------------------------------------------------------------------------
// start
// ---------------------------------------------------------------------------

#[test]
fn ralph_start_runs_successfully() {
    cargo_bin_cmd!("ralph")
        .arg("start")
        .assert()
        .success()
        .stdout(predicate::str::contains("start"));
}

#[test]
fn ralph_start_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["start", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Start the Ralph daemon"));
}

// ---------------------------------------------------------------------------
// stop
// ---------------------------------------------------------------------------

#[test]
fn ralph_stop_runs_successfully() {
    cargo_bin_cmd!("ralph")
        .arg("stop")
        .assert()
        .success()
        .stdout(predicate::str::contains("stop"));
}

#[test]
fn ralph_stop_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["stop", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Stop the Ralph daemon"));
}

// ---------------------------------------------------------------------------
// status
// ---------------------------------------------------------------------------

#[test]
fn ralph_status_runs_successfully() {
    cargo_bin_cmd!("ralph")
        .arg("status")
        .assert()
        .success()
        .stdout(predicate::str::contains("status"));
}

#[test]
fn ralph_status_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["status", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Query pipeline status"));
}

#[test]
fn ralph_status_accepts_detail_flag() {
    cargo_bin_cmd!("ralph")
        .args(["status", "--detail"])
        .assert()
        .success()
        .stdout(predicate::str::contains("status"));
}

// ---------------------------------------------------------------------------
// diagnose
// ---------------------------------------------------------------------------

#[test]
fn ralph_diagnose_runs_with_story_id() {
    cargo_bin_cmd!("ralph")
        .args(["diagnose", "42"])
        .assert()
        .success()
        .stdout(predicate::str::contains("diagnose"));
}

#[test]
fn ralph_diagnose_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["diagnose", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("diagnostic report"));
}

#[test]
fn ralph_diagnose_requires_story_id() {
    cargo_bin_cmd!("ralph")
        .arg("diagnose")
        .assert()
        .failure()
        .stderr(predicate::str::contains("STORY_ID"));
}

#[test]
fn ralph_diagnose_rejects_non_numeric_story_id() {
    cargo_bin_cmd!("ralph")
        .args(["diagnose", "abc"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("invalid value"));
}

// ---------------------------------------------------------------------------
// retry
// ---------------------------------------------------------------------------

#[test]
fn ralph_retry_runs_with_story_id() {
    cargo_bin_cmd!("ralph")
        .args(["retry", "7"])
        .assert()
        .success()
        .stdout(predicate::str::contains("retry"));
}

#[test]
fn ralph_retry_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["retry", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Re-feed a story"));
}

#[test]
fn ralph_retry_requires_story_id() {
    cargo_bin_cmd!("ralph")
        .arg("retry")
        .assert()
        .failure()
        .stderr(predicate::str::contains("STORY_ID"));
}

#[test]
fn ralph_retry_rejects_non_numeric_story_id() {
    cargo_bin_cmd!("ralph")
        .args(["retry", "xyz"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("invalid value"));
}

// ---------------------------------------------------------------------------
// init
// ---------------------------------------------------------------------------

#[test]
fn ralph_init_runs_successfully() {
    cargo_bin_cmd!("ralph")
        .arg("init")
        .assert()
        .success()
        .stdout(predicate::str::contains("init"));
}

#[test]
fn ralph_init_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["init", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Initialize Ralph"));
}

// ---------------------------------------------------------------------------
// watch
// ---------------------------------------------------------------------------

#[test]
fn ralph_watch_runs_successfully() {
    cargo_bin_cmd!("ralph")
        .arg("watch")
        .assert()
        .success()
        .stdout(predicate::str::contains("watch"));
}

#[test]
fn ralph_watch_help_shows_description() {
    cargo_bin_cmd!("ralph")
        .args(["watch", "--help"])
        .assert()
        .success()
        .stdout(predicate::str::contains("Live TUI monitoring"));
}
