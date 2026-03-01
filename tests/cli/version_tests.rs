//! ATDD CLI E2E tests for version output.
//!
//! Story 1.1 / AC3: `ralph --version` outputs `ralph 0.1.0`

use assert_cmd::cargo_bin_cmd;
use predicates::prelude::*;

#[test]
fn ralph_version_shows_correct_format() {
    cargo_bin_cmd!("ralph")
        .arg("--version")
        .assert()
        .success()
        .stdout(predicate::str::contains("ralph 0.1.0"));
}

#[test]
fn ralph_version_contains_semver() {
    cargo_bin_cmd!("ralph")
        .arg("--version")
        .assert()
        .success()
        .stdout(predicate::str::is_match(r"\d+\.\d+\.\d+").expect("valid regex"));
}

#[test]
fn ralph_short_version_flag() {
    cargo_bin_cmd!("ralph")
        .arg("-V")
        .assert()
        .success()
        .stdout(predicate::str::contains(env!("CARGO_PKG_VERSION")));
}
