//! Integration tests for ralph-config: file-based loading, edge cases, error handling.
//!
//! These tests complement the unit tests in config_tests.rs by focusing on
//! file system interactions and boundary conditions.

use std::path::PathBuf;

use ralph_config::config::RalphConfig;
use rstest::*;
use tempfile::TempDir;

// ─── fixtures ──────────────────────────────────────────────────────

/// Fixture: temporary directory for config files.
#[fixture]
fn config_dir() -> (TempDir, PathBuf) {
    let dir = TempDir::new().unwrap();
    let path = dir.path().to_path_buf();
    (dir, path)
}

// ─── happy path ────────────────────────────────────────────────────

#[rstest]
fn load_from_valid_toml_file(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(&config_path, "max_workers = 3").unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    let config: RalphConfig = toml::from_str(&content).unwrap();
    assert_eq!(config.max_workers, Some(3));
}

#[rstest]
fn load_from_empty_file_gives_defaults(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(&config_path, "").unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    let config: RalphConfig = toml::from_str(&content).unwrap();
    assert_eq!(config.max_workers, None);
}

// ─── error handling ────────────────────────────────────────────────

#[rstest]
fn missing_file_returns_io_error(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("nonexistent.toml");

    let result = std::fs::read_to_string(&config_path);
    assert!(result.is_err(), "reading missing file should return error");
}

#[rstest]
fn invalid_toml_returns_parse_error(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(&config_path, "this is not valid toml = [[[").unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    let result = toml::from_str::<RalphConfig>(&content);
    assert!(result.is_err(), "invalid TOML should return parse error");
}

#[rstest]
fn wrong_type_for_max_workers_returns_error(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(&config_path, "max_workers = \"not a number\"").unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    let result = toml::from_str::<RalphConfig>(&content);
    assert!(
        result.is_err(),
        "string value for max_workers should fail deserialization"
    );
}

// ─── edge cases ────────────────────────────────────────────────────

#[rstest]
#[case(0)]
#[case(1)]
#[case(100)]
fn max_workers_boundary_values(#[case] value: u32, config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(&config_path, format!("max_workers = {value}")).unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    let config: RalphConfig = toml::from_str(&content).unwrap();
    assert_eq!(config.max_workers, Some(value));
}

#[rstest]
fn negative_max_workers_returns_error(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(&config_path, "max_workers = -1").unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    let result = toml::from_str::<RalphConfig>(&content);
    assert!(
        result.is_err(),
        "negative max_workers should fail for u32 field"
    );
}

#[rstest]
fn unknown_fields_are_silently_ignored(config_dir: (TempDir, PathBuf)) {
    let (_guard, path) = config_dir;
    let config_path = path.join("ralph.toml");
    std::fs::write(
        &config_path,
        "max_workers = 2\nunknown_field = \"hello\"\nanother = 42",
    )
    .unwrap();

    let content = std::fs::read_to_string(&config_path).unwrap();
    // By default, serde Deserialize ignores unknown fields
    let config: RalphConfig = toml::from_str(&content).unwrap();
    assert_eq!(config.max_workers, Some(2));
}

// ─── default construction ──────────────────────────────────────────

#[rstest]
fn default_config_all_fields_are_none() {
    let config = RalphConfig::default();
    assert_eq!(
        config.max_workers, None,
        "default max_workers should be None"
    );
}
