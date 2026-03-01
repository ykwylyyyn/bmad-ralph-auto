//! Integration tests for the worker subsystem using the `fake-claude` test binary.
//!
//! These tests exercise the full process lifecycle:
//! fake-claude binary modes, output parsing pipeline, and RealClaudeProcess API.

mod fake_claude_tests;
mod output_integration;
mod real_process_tests;

use std::path::PathBuf;

/// Resolve the `fake-claude` binary path from the workspace target directory.
///
/// The binary is built as a workspace member and lands in `target/debug/`.
fn fake_claude_bin() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    // Navigate from crates/ralph/ up to workspace root
    let workspace_root = manifest_dir
        .ancestors()
        .nth(2)
        .expect("workspace root should exist");

    let debug_path = workspace_root
        .join("target")
        .join("debug")
        .join("fake-claude");
    let release_path = workspace_root
        .join("target")
        .join("release")
        .join("fake-claude");

    if debug_path.exists() {
        debug_path
    } else if release_path.exists() {
        release_path
    } else {
        panic!(
            "fake-claude binary not found at {} or {}. Run `cargo build -p fake-claude` first.",
            debug_path.display(),
            release_path.display()
        );
    }
}
