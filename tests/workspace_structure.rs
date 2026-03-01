//! Workspace structure regression tests (AC1 — Build & Workspace Structure).
//!
//! These tests verify that the Cargo workspace contains the expected 5 crates
//! with correct dependency flow. They parse TOML files directly and validate
//! structural invariants.

use std::fs;
use std::path::PathBuf;
use toml::Value;

/// Resolve the workspace root directory.
///
/// When run from the workspace root package, `CARGO_MANIFEST_DIR` points to
/// the workspace root.  When run from `crates/ralph/`, we walk up to find the
/// root `Cargo.toml` that contains `[workspace]`.
fn workspace_root() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

    // Check if manifest_dir itself is the workspace root.
    let candidate = manifest_dir.join("Cargo.toml");
    if candidate.exists() {
        let content = fs::read_to_string(&candidate).unwrap();
        if content.contains("[workspace]") {
            return manifest_dir;
        }
    }

    // Walk up until we find a Cargo.toml with [workspace].
    let mut dir = manifest_dir.as_path();
    loop {
        dir = dir.parent().unwrap_or_else(|| {
            panic!(
                "could not find workspace root from {}",
                manifest_dir.display()
            )
        });
        let cargo_toml = dir.join("Cargo.toml");
        if cargo_toml.exists() {
            let content = fs::read_to_string(&cargo_toml).unwrap();
            if content.contains("[workspace]") {
                return dir.to_path_buf();
            }
        }
    }
}

/// Parse a Cargo.toml file into a `toml::Value`.
fn parse_cargo_toml(path: &std::path::Path) -> Value {
    let content = fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("failed to read {}: {}", path.display(), e));
    toml::from_str::<Value>(&content)
        .unwrap_or_else(|e| panic!("failed to parse {}: {}", path.display(), e))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[test]
fn workspace_has_expected_member_count() {
    let root = workspace_root();
    let parsed = parse_cargo_toml(&root.join("Cargo.toml"));

    let members = parsed["workspace"]["members"]
        .as_array()
        .expect("workspace.members should be an array");

    assert_eq!(
        members.len(),
        6,
        "workspace should have exactly 6 members (5 crates + fake-claude), found: {:?}",
        members
    );
}

#[test]
fn workspace_members_have_correct_names() {
    let root = workspace_root();
    let parsed = parse_cargo_toml(&root.join("Cargo.toml"));

    let members: Vec<String> = parsed["workspace"]["members"]
        .as_array()
        .expect("workspace.members should be an array")
        .iter()
        .map(|v| {
            v.as_str()
                .expect("each member should be a string")
                .to_string()
        })
        .collect();

    let expected = [
        "crates/ralph",
        "crates/ralph-common",
        "crates/ralph-config",
        "crates/ralph-worker",
        "crates/ralph-pipeline",
        "tests/fake-claude",
    ];

    for expected_member in &expected {
        assert!(
            members.contains(&expected_member.to_string()),
            "workspace members should contain '{}', found: {:?}",
            expected_member,
            members
        );
    }

    assert_eq!(
        members.len(),
        expected.len(),
        "workspace should have exactly {} members, found: {:?}",
        expected.len(),
        members
    );
}

#[test]
fn ralph_common_has_no_internal_dependencies() {
    let root = workspace_root();
    let parsed = parse_cargo_toml(&root.join("crates/ralph-common/Cargo.toml"));

    if let Some(deps) = parsed.get("dependencies").and_then(|d| d.as_table()) {
        for dep_name in deps.keys() {
            assert!(
                !dep_name.starts_with("ralph-"),
                "ralph-common should not depend on any ralph-* crate, but depends on '{}'",
                dep_name
            );
        }
    }
    // If there is no [dependencies] section at all, that also passes.
}

#[test]
fn ralph_depends_on_all_sibling_crates() {
    let root = workspace_root();
    let parsed = parse_cargo_toml(&root.join("crates/ralph/Cargo.toml"));

    let deps = parsed["dependencies"]
        .as_table()
        .expect("ralph should have a [dependencies] table");

    let expected_siblings = [
        "ralph-common",
        "ralph-config",
        "ralph-worker",
        "ralph-pipeline",
    ];

    for sibling in &expected_siblings {
        assert!(
            deps.contains_key(*sibling),
            "ralph should depend on '{}', found deps: {:?}",
            sibling,
            deps.keys().collect::<Vec<_>>()
        );
    }
}

#[test]
fn ralph_binary_is_produced() {
    // Verify that `cargo build` produces a binary named `ralph`.
    // `cargo_bin!` resolves the binary path at compile time via CARGO_BIN_EXE_ralph.
    let path = assert_cmd::cargo_bin!("ralph");
    assert!(
        path.exists(),
        "ralph binary should exist at {}",
        path.display()
    );
}

#[test]
fn all_crates_have_workspace_version() {
    let root = workspace_root();

    let crate_dirs = [
        "crates/ralph",
        "crates/ralph-common",
        "crates/ralph-config",
        "crates/ralph-worker",
        "crates/ralph-pipeline",
    ];

    for crate_dir in &crate_dirs {
        let cargo_path = root.join(crate_dir).join("Cargo.toml");
        let content = fs::read_to_string(&cargo_path)
            .unwrap_or_else(|e| panic!("failed to read {}: {}", cargo_path.display(), e));
        let parsed: Value = toml::from_str(&content)
            .unwrap_or_else(|e| panic!("failed to parse {}: {}", cargo_path.display(), e));

        // version.workspace = true can appear as:
        //   [package]
        //   version.workspace = true
        //
        // In TOML this parses as package.version being a table { workspace = true }.
        let version = &parsed["package"]["version"];

        match version {
            Value::Table(tbl) => {
                let ws = tbl
                    .get("workspace")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);
                assert!(
                    ws,
                    "{} should use version.workspace = true, found version = {:?}",
                    crate_dir, version
                );
            }
            other => {
                panic!(
                    "{} should use version.workspace = true, but version is {:?}",
                    crate_dir, other
                );
            }
        }
    }
}
