---
stepsCompleted:
  - step-01-preflight
  - step-02-generate-pipeline
  - step-03-configure-quality-gates
  - step-04-validate-and-summary
lastStep: step-04-validate-and-summary
lastSaved: 2026-06-30
ci_platform: github-actions
test_stack_type: backend
---

# CI Pipeline Progress — bmad-ralph

## Platform

- **CI platform:** GitHub Actions
- **Config path:** `.github/workflows/ci.yml`
- **Local reproduction:** `scripts/ci-local.sh`

## Pipeline Stages

| Stage | Job | Command |
|-------|-----|---------|
| Python tests | `python` | `pip install pyyaml && make test-all` |
| Rust fmt | `rust` | `cargo fmt --all -- --check` |
| Rust build | `rust` | `cargo build --workspace` |
| Rust clippy | `rust` | `cargo clippy --workspace -- -D warnings` |
| Rust tests | `rust` | `cargo test --workspace` |
| Quality gate | `quality-gate` | Requires python + rust success |

## Quality Gates

- **P0:** All Python unit/integration tests pass (`make test-all`)
- **P0:** Rust formatting, clippy (zero warnings), and full workspace tests pass
- **Burn-in:** Intentionally skipped — backend-only stack (TEA guidance)

## Triggers

- `push` to `main`
- `pull_request` targeting `main`
- Concurrency: cancel in-progress runs on same ref

## Next Steps

1. Merge PR with `.github/workflows/ci.yml`
2. Enable branch protection on `main` requiring the `Quality Gate` check
3. Run `scripts/ci-local.sh` before pushing
