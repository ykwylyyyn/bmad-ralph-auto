from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from ralph.common.db import StateStore
from ralph.common.protocol import Request
from ralph.config import RalphConfig
from ralph.pipeline.engine import PipelineEngine

from .ipc import IpcServer, request_daemon, status_response
from .runtime import RuntimePaths


@dataclass(frozen=True, slots=True)
class DaemonStatus:
    state: str
    pid: int | None
    project_dir: str
    max_workers: int
    started_at: str | None = None
    heartbeat_at: str | None = None
    message: str = ""


def start_daemon(project_dir: str | Path, config: RalphConfig) -> DaemonStatus:
    paths = RuntimePaths(Path(project_dir).resolve())
    paths.ensure()
    store = _initialize_database(paths)
    store.close()

    current = read_status(paths.project_dir)
    if current.state == "running" and current.pid is not None and _pid_exists(current.pid):
        return current

    _remove_if_exists(paths.stop_file)
    command = [
        sys.executable,
        "-m",
        "ralph",
        "_daemon",
        "--project-dir",
        str(paths.project_dir),
        "--max-workers",
        str(config.effective().max_workers),
    ]
    kwargs: dict[str, object] = {
        "cwd": str(paths.project_dir),
        "env": _subprocess_env(),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "start_new_session": os.name != "nt",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(command, **kwargs)

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = read_status(paths.project_dir)
        if status.state == "running" and status.pid == process.pid:
            return status
        time.sleep(0.05)

    return DaemonStatus(
        state="starting",
        pid=process.pid,
        project_dir=str(paths.project_dir),
        max_workers=config.effective().max_workers or 5,
        message="daemon process started but heartbeat is not ready",
    )


def stop_daemon(project_dir: str | Path, timeout_secs: float = 5.0) -> DaemonStatus:
    paths = RuntimePaths(Path(project_dir).resolve())
    paths.ensure()
    status = read_status(paths.project_dir)
    if status.state != "running":
        return status

    response = request_daemon(paths, Request(type="stop", graceful=True), timeout_secs=1.0)
    if response.type == "error":
        paths.stop_file.write_text(_now(), encoding="utf-8")
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        status = read_status(paths.project_dir)
        if status.state == "stopped":
            if status.pid is not None:
                _wait_for_pid_exit(status.pid, timeout_secs=1.0)
            return status
        time.sleep(0.05)

    if status.pid is not None:
        _terminate_pid(status.pid)
        time.sleep(0.2)
        status = read_status(paths.project_dir)
        if status.state == "stopped":
            if status.pid is not None:
                _wait_for_pid_exit(status.pid, timeout_secs=1.0)
            return status

    return DaemonStatus(
        state="stopping",
        pid=status.pid,
        project_dir=str(paths.project_dir),
        max_workers=status.max_workers,
        started_at=status.started_at,
        heartbeat_at=status.heartbeat_at,
        message="daemon did not stop before timeout",
    )


def read_status(project_dir: str | Path) -> DaemonStatus:
    paths = RuntimePaths(Path(project_dir).resolve())
    if not paths.status_file.exists():
        return DaemonStatus(
            state="stopped",
            pid=None,
            project_dir=str(paths.project_dir),
            max_workers=5,
            message="daemon has not been started",
        )
    try:
        data = json.loads(paths.status_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DaemonStatus(
            state="unknown",
            pid=None,
            project_dir=str(paths.project_dir),
            max_workers=5,
            message="status file is not valid JSON",
        )
    status = DaemonStatus(**data)
    if status.state == "running" and status.pid is not None and not _pid_exists(status.pid):
        stopped = DaemonStatus(
            state="stopped",
            pid=status.pid,
            project_dir=status.project_dir,
            max_workers=status.max_workers,
            started_at=status.started_at,
            heartbeat_at=status.heartbeat_at,
            message="daemon process is no longer running",
        )
        _write_status(paths, stopped)
        return stopped
    return status


def run_daemon(project_dir: str | Path, config: RalphConfig, heartbeat_secs: float = 0.2) -> int:
    paths = RuntimePaths(Path(project_dir).resolve())
    paths.ensure()
    store = StateStore.open(paths.database_file)
    recovered = store.load_snapshot()
    engine = PipelineEngine(
        store,
        project_dir=paths.project_dir,
        max_workers=config.effective().max_workers or 5,
        worktrees_dir=paths.worktrees_dir,
    )
    pipeline_state = engine.initialize()
    started_at = _now()
    pid = os.getpid()
    paths.pid_file.write_text(str(pid), encoding="utf-8")
    ipc = IpcServer(paths)
    ipc.start()
    should_stop = False
    recovery_message = (
        f"recovered {len(recovered.stories)} stories and {len(recovered.workers)} workers from database"
        if recovered.stories or recovered.workers
        else ""
    )
    status_message = recovery_message or f"pipeline {pipeline_state.value}"

    try:
        while not should_stop and not paths.stop_file.exists():
            tick = engine.tick()
            status = DaemonStatus(
                state="running",
                pid=pid,
                project_dir=str(paths.project_dir),
                max_workers=config.effective().max_workers or 5,
                started_at=started_at,
                heartbeat_at=_now(),
                message=engine.status_message(tick),
            )
            _write_status(paths, status)
            should_stop = ipc.poll(lambda request: _handle_request(request, status, paths))
            if not should_stop:
                time.sleep(heartbeat_secs)
    finally:
        engine.shutdown()
        store.close()
        ipc.close()
        _remove_if_exists(paths.pid_file)
        _remove_if_exists(paths.stop_file)
        _write_status(
            paths,
            DaemonStatus(
                state="stopped",
                pid=pid,
                project_dir=str(paths.project_dir),
                max_workers=config.effective().max_workers or 5,
                started_at=started_at,
                heartbeat_at=_now(),
                message="daemon stopped gracefully",
            ),
        )
    return 0


def _handle_request(request: Request, status: DaemonStatus, paths: RuntimePaths):
    if request.type == "status":
        return status_response(status)
    if request.type == "stop":
        paths.stop_file.write_text(_now(), encoding="utf-8")
        return status_response(
            DaemonStatus(
                state="stopping",
                pid=status.pid,
                project_dir=status.project_dir,
                max_workers=status.max_workers,
                started_at=status.started_at,
                heartbeat_at=_now(),
                message="stop requested",
            )
        )
    return status_response(
        DaemonStatus(
            state="running",
            pid=status.pid,
            project_dir=status.project_dir,
            max_workers=status.max_workers,
            started_at=status.started_at,
            heartbeat_at=status.heartbeat_at,
            message=f"unsupported request: {request.type}",
        )
    )


def _initialize_database(paths: RuntimePaths) -> StateStore:
    return StateStore.open(paths.database_file)


def _write_status(paths: RuntimePaths, status: DaemonStatus) -> None:
    paths.status_file.write_text(json.dumps(asdict(status), indent=2, sort_keys=True), encoding="utf-8")


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _pid_exists(pid: int) -> bool:
    if pid < 1:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _wait_for_pid_exit(pid: int, timeout_secs: float) -> bool:
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return True
        time.sleep(0.05)
    return not _pid_exists(pid)


def _terminate_pid(pid: int) -> None:
    if pid < 1:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.kill(pid, 15)
    except ProcessLookupError:
        return


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src_dir = str(Path(__file__).resolve().parents[2])
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_dir if not current else f"{src_dir}{os.pathsep}{current}"
    return env


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
