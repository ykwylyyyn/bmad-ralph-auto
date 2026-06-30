# CI Pipeline Progress — bmad-ralph

## Platform

- **CI platform:** GitHub Actions
- **Config path:** `.github/workflows/ci.yml`
- **Local reproduction:** `scripts/ci-local.sh`

## Pipeline Stages

| Stage | Job | Command |
|-------|-----|---------|
| Python tests | `python` | `pip install pyyaml && make test-all` |

## Quality Gates

- **P0:** All Python unit/integration tests pass (`make test-all`)

## Triggers

- `push` to `main`
- `pull_request` targeting `main`
- Concurrency: cancel in-progress runs on same ref

## Next Steps

1. Enable branch protection on `main` requiring the **Python Tests** check
2. Run `scripts/ci-local.sh` before pushing
