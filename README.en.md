# Ralph

[中文](README.zh-CN.md) | English

Autonomous SDLC pipeline runner, now being migrated to a Python CLI daemon that orchestrates parallel Claude Code worker sessions to execute BMAD stories with self-healing capabilities.

Ralph pairs with [BMAD-METHOD](https://github.com/bmad-method) for planning, shifting delivery from human-in-the-loop to human-on-the-loop.

## How It Works

1. BMAD produces sprint plans with sequenced, dependency-mapped stories.
2. Ralph daemon ingests the plan and analyzes parallelization opportunities.
3. Concurrent Claude Code workers execute stories in isolated git worktrees.
4. Three-layer self-healing handles retry, worker restart, and diagnose escalation.
5. Developers monitor progress via terminal status and dashboard commands.

## Architecture

Python package with the same bounded contexts as the original Rust plan:

```text
src/ralph/cli.py          # CLI entry point
src/ralph/pipeline/       # State machine and scheduling contracts
src/ralph/worker/         # Claude process spawning and output parsing
src/ralph/config/         # TOML config loading
src/ralph/common/         # Shared models, protocol types, SQLite schema
```

Key choices: SQLite + WAL for persistence, JSON request/response protocol types, and `asyncio` for process management.

The previous Rust workspace remains in the repository during migration as reference material.

## CLI

```bash
ralph start      # Start daemon, begin processing sprint plan
ralph stop       # Graceful shutdown
ralph status     # Pipeline state, story progress, worker health
ralph watch      # Live terminal dashboard
ralph diagnose   # Diagnostic report for failed stories
ralph retry      # Re-feed corrected stories into pipeline
ralph init       # Initialize Ralph on a project
```

Current Python commands are functional stubs matching the existing CLI contract.

## Development Status

**Early development** - Python migration foundation in progress.

### Completed

- Python package scaffold and `ralph` CLI entry point
- Shared domain models, protocol DTOs, and SQLite schema
- Config loading from TOML
- Claude process abstraction and output parser
- Python regression tests for CLI, config, common models/schema, and worker output parsing

## Build And Test

```bash
python -m ralph --help
make test-all
```

Requires Python 3.11 or newer. Use `PYTHONPATH=src python -m ralph --help` when running directly from a checkout without installing the package.

Legacy Rust targets are still available during migration when Cargo is installed:

```bash
make rust-test
```

## License

MIT
