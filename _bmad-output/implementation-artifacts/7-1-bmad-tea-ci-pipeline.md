# Story 7.1: BMAD TEA CI Pipeline

## Summary

Scaffolded GitHub Actions CI/CD quality pipeline per `/bmad-tea-testarch-ci` workflow (Phase 3).

## Deliverables

### `.github/workflows/ci.yml`
- Parallel **Python** and **Rust** jobs
- Python: `make test-all` (146 tests) with PyYAML dependency
- Rust: `cargo fmt --check`, `cargo build`, `cargo clippy -D warnings`, `cargo test --workspace`
- **Quality gate** job aggregates pass/fail for branch protection

### `scripts/ci-local.sh`
- Local reproduction of all CI stages

### BMAD artifacts
- `_bmad-output/test-artifacts/ci-pipeline-progress.md`

## Design Decisions

- **Backend-only stack:** No Playwright/browser install; burn-in skipped per TEA guidance
- **No sharding:** Test suite size (~146 Python + Rust integration) fits single-runner jobs
- **Cargo cache:** `Swatinem/rust-cache@v2` for faster Rust builds

## Verification

```bash
chmod +x scripts/ci-local.sh
./scripts/ci-local.sh
```
