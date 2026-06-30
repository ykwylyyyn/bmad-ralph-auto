# Story 7.1: BMAD TEA CI Pipeline

## Summary

GitHub Actions CI/CD quality pipeline per `/bmad-tea-testarch-ci` workflow (Phase 3).

## Deliverables

### `.github/workflows/ci.yml`
- **Python** job: `make test-all` with PyYAML dependency

### `scripts/ci-local.sh`
- Local reproduction of CI stages

### BMAD artifacts
- `_bmad-output/test-artifacts/ci-pipeline-progress.md`

## Design Decisions

- **Python-only stack:** Rust workspace removed after migration to Python CLI
- **Backend-only:** No Playwright/browser install; burn-in skipped per TEA guidance
- **No sharding:** Test suite fits single-runner job

## Verification

```bash
chmod +x scripts/ci-local.sh
./scripts/ci-local.sh
```
