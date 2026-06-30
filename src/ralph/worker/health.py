from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Literal

from ralph.common.models import WorkerHealth, WorkerState

from .process import ClaudeOutput

ExitKind = Literal["completed", "unexpected", "killed"]


@dataclass(frozen=True, slots=True)
class WorkerHealthReport:
    worker_id: int
    state: WorkerState
    health: WorkerHealth
    pid: int | None
    is_running: bool


def pid_is_alive(pid: int | None) -> bool:
    if pid is None or pid < 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def classify_exit(output: ClaudeOutput, *, killed: bool) -> ExitKind:
    if killed:
        return "killed"
    if output.exit_code == 0:
        return "completed"
    if output.stdout.strip():
        try:
            json.loads(output.stdout)
            return "completed"
        except json.JSONDecodeError:
            pass
    return "unexpected"


def health_for_active_worker(pid: int | None, *, is_running: bool) -> WorkerHealth:
    if not is_running:
        return WorkerHealth.UNKNOWN
    if pid_is_alive(pid):
        return WorkerHealth.HEALTHY
    return WorkerHealth.UNRESPONSIVE


def health_for_idle_worker(state: WorkerState) -> WorkerHealth:
    if state == WorkerState.FAILED:
        return WorkerHealth.DEGRADED
    return WorkerHealth.HEALTHY
