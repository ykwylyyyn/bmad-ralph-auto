from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

BMAD_SUBMODULE_DIR = "_bmad"
DEFAULT_BMAD_SUBMODULE_URL = "https://github.com/bmad-code-org/BMAD-METHOD.git"
BMAD_PIN_FILENAME = "bmad-pin.json"
PLANNING_ARTIFACTS_DIR = Path("_bmad-output") / "planning-artifacts"
IMPLEMENTATION_ARTIFACTS_DIR = Path("_bmad-output") / "implementation-artifacts"
_REQUIRED_BMAD_PATHS = (
    Path("bmm") / "workflows",
    Path("bmm") / "config.yaml",
)
_PLANNING_WORKFLOW_KEYWORDS = (
    "planning",
    "prd",
    "architecture",
    "ux",
    "sprint-plan",
    "create-epic",
    "create-story",
)


@dataclass(frozen=True, slots=True)
class BmadIntegrationResult:
    bmad_path: Path
    action: str
    pinned_ref: str | None
    planning_workflows: tuple[str, ...]
    message: str = ""


def integrate_bmad(project_dir: str | Path, *, submodule_url: str | None = None) -> BmadIntegrationResult:
    root = Path(project_dir).resolve()
    ensure_planning_output_dirs(root)

    bmad_path = root / BMAD_SUBMODULE_DIR
    if bmad_path.is_dir() and validate_bmad_layout(bmad_path):
        pinned_ref = _resolve_pinned_ref(root, bmad_path)
        _write_pin_file(root, submodule_url=_submodule_url(root) or "local", pinned_ref=pinned_ref)
        workflows = tuple(list_planning_workflows(bmad_path))
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="validated",
            pinned_ref=pinned_ref,
            planning_workflows=workflows,
            message="existing BMAD submodule validated",
        )

    if not _is_git_repository(root):
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="skipped",
            pinned_ref=None,
            planning_workflows=(),
            message="project is not a git repository; add BMAD manually under _bmad/",
        )

    url = submodule_url or os.environ.get("RALPH_BMAD_SUBMODULE_URL", DEFAULT_BMAD_SUBMODULE_URL)
    git_config = _submodule_git_config(url)
    add_result = _run_git(
        root,
        "submodule",
        "add",
        "--depth",
        "1",
        url,
        BMAD_SUBMODULE_DIR,
        extra_config=git_config,
    )
    if add_result.returncode != 0:
        stderr = add_result.stderr.strip() or add_result.stdout.strip()
        if "already exists" in stderr.lower():
            sync_result = _run_git(root, "submodule", "update", "--init", "--depth", "1", BMAD_SUBMODULE_DIR)
            if sync_result.returncode != 0:
                return BmadIntegrationResult(
                    bmad_path=bmad_path,
                    action="failed",
                    pinned_ref=None,
                    planning_workflows=(),
                    message=sync_result.stderr.strip() or "failed to initialize BMAD submodule",
                )
        else:
            return BmadIntegrationResult(
                bmad_path=bmad_path,
                action="failed",
                pinned_ref=None,
                planning_workflows=(),
                message=stderr or "failed to add BMAD submodule",
            )

    if not validate_bmad_layout(bmad_path):
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="failed",
            pinned_ref=None,
            planning_workflows=(),
            message="BMAD submodule added but required planning workflow layout is missing",
        )

    pinned_ref = _resolve_pinned_ref(root, bmad_path)
    _write_pin_file(root, submodule_url=url, pinned_ref=pinned_ref)
    workflows = tuple(list_planning_workflows(bmad_path))
    return BmadIntegrationResult(
        bmad_path=bmad_path,
        action="initialized",
        pinned_ref=pinned_ref,
        planning_workflows=workflows,
        message="BMAD submodule configured",
    )


def ensure_planning_output_dirs(project_dir: str | Path) -> None:
    root = Path(project_dir).resolve()
    (root / PLANNING_ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)
    (root / IMPLEMENTATION_ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)


def validate_bmad_layout(bmad_dir: str | Path) -> bool:
    root = Path(bmad_dir)
    return all((root / relative).exists() for relative in _REQUIRED_BMAD_PATHS)


def list_planning_workflows(bmad_dir: str | Path) -> list[str]:
    workflows_root = Path(bmad_dir) / "bmm" / "workflows"
    if not workflows_root.is_dir():
        return []

    discovered: list[str] = []
    for path in sorted(workflows_root.rglob("workflow.yaml")):
        relative = path.parent.relative_to(workflows_root).as_posix()
        lowered = relative.lower()
        if any(keyword in lowered for keyword in _PLANNING_WORKFLOW_KEYWORDS):
            discovered.append(relative)
    return discovered


def read_bmad_pin(project_dir: str | Path) -> dict[str, object] | None:
    pin_path = Path(project_dir).resolve() / ".ralph" / BMAD_PIN_FILENAME
    if not pin_path.exists():
        return None
    try:
        data = json.loads(pin_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def submodule_update_hint() -> str:
    return f"git submodule update --remote {BMAD_SUBMODULE_DIR}"


def _write_pin_file(project_dir: Path, *, submodule_url: str, pinned_ref: str | None) -> None:
    pin_dir = project_dir / ".ralph"
    pin_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "path": BMAD_SUBMODULE_DIR,
        "url": submodule_url,
        "ref": pinned_ref,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "update_command": submodule_update_hint(),
    }
    (pin_dir / BMAD_PIN_FILENAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolve_pinned_ref(project_dir: Path, bmad_path: Path) -> str | None:
    submodule_ref = _submodule_ref(project_dir, bmad_path)
    if submodule_ref:
        return submodule_ref
    return _git_head(bmad_path)


def _submodule_url(project_dir: Path) -> str | None:
    gitmodules = project_dir / ".gitmodules"
    if not gitmodules.exists():
        return None
    for line in gitmodules.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("url ="):
            return stripped.split("=", 1)[1].strip()
    return None


def _submodule_ref(project_dir: Path, bmad_path: Path) -> str | None:
    result = _run_git(project_dir, "submodule", "status", "--", str(bmad_path.relative_to(project_dir)))
    if result.returncode != 0:
        return None
    line = result.stdout.strip().splitlines()
    if not line:
        return None
    parts = line[0].strip().split()
    if len(parts) < 2:
        return None
    commit = parts[0].lstrip("+-U")
    if commit.startswith("-"):
        return None
    return commit


def _git_head(path: Path) -> str | None:
    result = _run_git(path, "rev-parse", "HEAD")
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _is_git_repository(project_dir: Path) -> bool:
    result = _run_git(project_dir, "rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


def _submodule_git_config(url: str) -> list[str]:
    if url.startswith("file:") or url.startswith("/"):
        return ["protocol.file.allow=always"]
    return []


def _run_git(cwd: Path, *args: str, extra_config: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    command = ["git"]
    for item in extra_config or []:
        command.extend(["-c", item])
    command.extend(args)
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
