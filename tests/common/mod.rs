//! Shared test utilities for workspace-level integration tests.
//!
//! Import in integration tests via:
//! ```rust
//! mod common;
//! ```

use std::path::{Path, PathBuf};
use tempfile::TempDir;

/// Creates an isolated project directory with a valid ralph.toml config.
/// Returns (TempDir, PathBuf) — keep TempDir alive for the duration of the test.
pub fn setup_project_dir(config_content: &str) -> (TempDir, PathBuf) {
    let dir = TempDir::new().expect("failed to create temp dir");
    let project_path = dir.path().to_path_buf();

    // Write ralph.toml
    let config_path = project_path.join("ralph.toml");
    std::fs::write(&config_path, config_content).expect("failed to write ralph.toml");

    // Create .ralph/ state directory
    let state_dir = project_path.join(".ralph");
    std::fs::create_dir_all(&state_dir).expect("failed to create .ralph dir");

    (dir, project_path)
}

/// Creates a minimal ralph.toml for testing.
pub fn default_config() -> String {
    r#"
[ralph]
max_workers = 3

[ralph.paths]
artifacts = "_bmad-output/planning-artifacts"
"#
    .to_string()
}

/// Initializes a temporary git repo for worker isolation tests.
pub fn setup_git_repo(path: &Path) {
    std::process::Command::new("git")
        .args(["init", "--initial-branch=main"])
        .current_dir(path)
        .output()
        .expect("failed to git init");

    std::process::Command::new("git")
        .args(["commit", "--allow-empty", "-m", "initial"])
        .current_dir(path)
        .output()
        .expect("failed to create initial commit");
}
