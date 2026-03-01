//! CLI integration tests using assert_cmd.
//!
//! These tests exercise the `ralph` binary as a black box,
//! verifying command output, exit codes, and side effects.

mod global_flags_tests;
mod help_tests;
mod subcommand_tests;
mod version_tests;

use assert_cmd::cargo_bin_cmd;
use predicates::prelude::*;

#[test]
fn ralph_without_args_shows_help() {
    cargo_bin_cmd!("ralph").assert().success();
}

#[test]
fn ralph_version_flag() {
    cargo_bin_cmd!("ralph")
        .arg("--version")
        .assert()
        .success()
        .stdout(predicate::str::contains(env!("CARGO_PKG_VERSION")));
}
