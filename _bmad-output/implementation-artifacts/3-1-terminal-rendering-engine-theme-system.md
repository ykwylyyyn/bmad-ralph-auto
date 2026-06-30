# Story 3.1: Terminal Rendering Engine & Theme System

## Summary

Introduced a shared `ralph.render` package providing semantic ANSI theming, terminal width adaptation, and reusable output components (Section Border, Spinner, Error Message). Wired theme resolution and components into `ralph start` / `ralph stop`.

## Changes

### `src/ralph/render/theme.py`
- `Theme` with semantic colors (green/yellow/red/dim/magenta/bold)
- `resolve_theme()` honors `--no-color`, `NO_COLOR`, TTY, and `TERM=dumb`
- `strip_ansi()` / `visible_length()` helpers

### `src/ralph/render/width.py`
- `layout_width()` clamps to 80–120 columns
- `story_name_limit()` tiers: 15 / 20 / 30 chars by terminal width
- `truncate_text()` with ellipsis

### `src/ralph/render/components.py`
- `section_border()` — `※ Name ═══════ context ※` pattern
- `Spinner` — Braille frames at 100ms, `✓`/`✗` completion markers
- `error_message()` — red bold label + detail + dim suggestion

### CLI integration
- Global `args.theme` resolved in `main()`
- `start` / `stop` use Spinner + Section Border output

### Other
- `daemon/ipc.py` — graceful fallback when socket missing
- `Makefile` — `python3` for test runner

## Tests

- `tests_python/test_render.py` (18 tests)
- Updated `tests_python/test_cli.py` for new output + `--no-color`

## Verification

```bash
make test-all  # 46 tests pass
```
