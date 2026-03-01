# Ralph Test Suite

## Setup

Ensure the Rust toolchain is installed:

```bash
# Uses rust-toolchain.toml (stable + clippy + rustfmt)
rustup show
```

Dev-dependencies are declared in each crate's `Cargo.toml` and resolved automatically by `cargo test`.

## Running Tests

```bash
# Run all tests (unit + integration) across workspace
cargo test --workspace

# Run tests for a specific crate
cargo test -p ralph-config
cargo test -p ralph-pipeline
cargo test -p ralph-worker
cargo test -p ralph-common

# Run CLI integration tests only (binary crate)
cargo test -p ralph

# Run a specific test by name
cargo test -p ralph-pipeline -- state_tests::tests::valid_transition

# Run tests with output (see println! in tests)
cargo test --workspace -- --nocapture

# Run tests with nextest (if installed, better output)
cargo nextest run --workspace
```

## Test Architecture

### Test Levels

| Level | Location | Tool | Purpose |
|-------|----------|------|---------|
| Unit | `crates/*/src/*_tests.rs` (inline `#[cfg(test)]`) | `rstest` + `mockall` | Pure logic, state transitions, config parsing |
| Integration | `tests/*.rs` | `rstest` + `tempfile` | Module interactions, SQLite state, git operations |
| CLI E2E | `tests/cli/` | `assert_cmd` + `predicates` | Black-box CLI binary testing |
| API E2E | `tests/` | `wiremock` | HTTP API endpoint tests (Unix socket / HTTP) |

### Key Patterns

#### rstest Fixtures

```rust
use rstest::*;

#[fixture]
fn config_dir() -> (TempDir, PathBuf) { /* ... */ }

#[rstest]
fn test_something(config_dir: (TempDir, PathBuf)) {
    // config_dir is injected automatically
}
```

#### Parametrized Tests

```rust
#[rstest]
#[case("max_workers = 1", Some(1))]
#[case("max_workers = 5", Some(5))]
#[case("", None)]
fn parse_max_workers(#[case] input: &str, #[case] expected: Option<u32>) {
    let config: RalphConfig = toml::from_str(input).unwrap();
    assert_eq!(config.max_workers, expected);
}
```

#### Async Tests

```rust
#[rstest]
#[tokio::test]
async fn worker_spawn_test(worktree_dir: (TempDir, PathBuf)) {
    // async test with fixture injection
}
```

#### CLI Integration Tests

```rust
use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn ralph_status_shows_no_daemon() {
    Command::cargo_bin("ralph").unwrap()
        .arg("status")
        .assert()
        .failure()
        .stderr(predicate::str::contains("no daemon running"));
}
```

### Directory Structure

```
tests/
├── common/
│   └── mod.rs          # Shared utilities (setup_project_dir, setup_git_repo)
├── cli/
│   └── mod.rs          # CLI integration tests (assert_cmd)
└── README.md           # This file

crates/
├── ralph-config/src/
│   └── config_tests.rs # Unit tests with rstest fixtures + parametrize
├── ralph-pipeline/src/
│   └── state_tests.rs  # State machine transition tests
└── ralph-worker/src/
    └── worker_tests.rs # Worker tests with async + fixture composition
```

## Best Practices

1. **Isolation**: Every test creates its own temp directory — no shared state
2. **Cleanup**: `TempDir` auto-cleans on drop — keep the guard alive during the test
3. **Determinism**: Use `rstest` fixtures for reproducible setup, no global state
4. **One assertion per test**: Use `#[case]` parametrize instead of multiple asserts
5. **Async**: Always use `#[tokio::test]` for async, combine with `#[rstest]` for fixtures
6. **Mocking**: Use `mockall` for trait mocking, prefer dependency injection over statics

## CI Integration

```yaml
# Example GitHub Actions step
- name: Run tests
  run: cargo test --workspace --locked

- name: Run clippy
  run: cargo clippy --workspace -- -D warnings

- name: Check formatting
  run: cargo fmt --workspace -- --check
```

## Test Crate Reference

| Crate | Docs | Purpose |
|-------|------|---------|
| [rstest](https://docs.rs/rstest) | Fixtures + parametrize |
| [assert_cmd](https://docs.rs/assert_cmd) | CLI binary testing |
| [predicates](https://docs.rs/predicates) | Fluent assertions |
| [tempfile](https://docs.rs/tempfile) | Temp dirs with auto-cleanup |
| [mockall](https://docs.rs/mockall) | Trait mocking |
| [wiremock](https://docs.rs/wiremock) | HTTP mock server |
