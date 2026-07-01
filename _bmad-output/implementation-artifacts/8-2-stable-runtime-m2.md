# Story 9.4 + 8.4 + X.1: Stable Runtime (M2)

## Summary

Implements Milestone M2 from `epic-8-11-agent-os-roadmap.md`:

- **Orphan recovery** — crash/stop 后 `initialize()` 回收无活跃 worker 的 `IN_PROGRESS`/`VERIFYING` story
- **Graceful shutdown** — `shutdown()` 回滚 `IN_PROGRESS`、requeue `VERIFYING`、重置 worker 状态
- **HEALING pipeline state** — 自愈进行中 `tick()` 报告 `PipelineState.HEALING`（不被 `RUNNING` 覆盖）
- **Diagnose verifier events** — `ralph diagnose` 时间线展示 `verification_failed` 详情
- **Feature flags** — `[verifier] enabled=false` 默认关闭，现有行为不变

## Changes

### `src/ralph/pipeline/recovery.py` (new)
- `recover_orphaned_stories()` — 孤儿 story requeue + 僵尸 worker 重置
- 记录 `orphan_recovery` pipeline event

### `src/ralph/pipeline/engine.py`
- `initialize()` 调用 orphan recovery
- `shutdown()` 完整回收（story + worker）
- `_evaluate_pipeline_state()` + `_stories_in_active_healing()` → `HEALING`
- `verification_failed` 事件含 command/exit_code/stderr

### `src/ralph/diagnose/snapshot.py`
- 合并 `verification_failed` pipeline events 到诊断时间线

## Tests

- `tests_python/test_recovery.py` (5)
- `tests_python/test_pipeline_engine.py` (+1 HEALING)
- `tests_python/test_diagnose.py` (+1 verifier events)

## Usage

无需额外配置。`verifier` 仍为 opt-in：

```toml
[verifier]
enabled = true
commands = ["make test-all"]
```

Stop/start 流程：

```powershell
ralph stop   # IN_PROGRESS → QUEUED
ralph start  # initialize() 回收孤儿 story，继续调度
```
