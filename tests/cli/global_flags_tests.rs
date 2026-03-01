//! E2E tests for global CLI flags.
//!
//! Verifies that --no-color, --quiet (-q), and --verbose (-v) flags
//! are accepted across all subcommands.

use assert_cmd::cargo_bin_cmd;
use predicates::prelude::*;

// ---------------------------------------------------------------------------
// --no-color
// ---------------------------------------------------------------------------

#[test]
fn ralph_no_color_flag_accepted_with_start() {
    cargo_bin_cmd!("ralph")
        .args(["--no-color", "start"])
        .assert()
        .success();
}

#[test]
fn ralph_no_color_flag_accepted_after_subcommand() {
    cargo_bin_cmd!("ralph")
        .args(["start", "--no-color"])
        .assert()
        .success();
}

// ---------------------------------------------------------------------------
// --quiet / -q
// ---------------------------------------------------------------------------

#[test]
fn ralph_quiet_flag_accepted() {
    cargo_bin_cmd!("ralph")
        .args(["--quiet", "status"])
        .assert()
        .success();
}

#[test]
fn ralph_quiet_short_flag_accepted() {
    cargo_bin_cmd!("ralph")
        .args(["-q", "status"])
        .assert()
        .success();
}

// ---------------------------------------------------------------------------
// --verbose / -v
// ---------------------------------------------------------------------------

#[test]
fn ralph_verbose_flag_accepted() {
    cargo_bin_cmd!("ralph")
        .args(["--verbose", "init"])
        .assert()
        .success();
}

#[test]
fn ralph_verbose_short_flag_accepted() {
    cargo_bin_cmd!("ralph")
        .args(["-v", "init"])
        .assert()
        .success();
}

// ---------------------------------------------------------------------------
// Combined flags
// ---------------------------------------------------------------------------

#[test]
fn ralph_quiet_and_no_color_combined() {
    cargo_bin_cmd!("ralph")
        .args(["-q", "--no-color", "stop"])
        .assert()
        .success();
}

#[test]
fn ralph_verbose_and_no_color_combined() {
    cargo_bin_cmd!("ralph")
        .args(["-v", "--no-color", "watch"])
        .assert()
        .success();
}

// ---------------------------------------------------------------------------
// Help output mentions global flags
// ---------------------------------------------------------------------------

#[test]
fn ralph_help_shows_no_color_option() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("no-color"));
}

#[test]
fn ralph_help_shows_quiet_option() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("quiet"));
}

#[test]
fn ralph_help_shows_verbose_option() {
    cargo_bin_cmd!("ralph")
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("verbose"));
}
