from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BMAD_SUBMODULE_DIR = "_bmad"
DEFAULT_BMAD_SUBMODULE_URL = "https://github.com/bmad-code-org/BMAD-METHOD.git"
DEFAULT_BMAD_NPM_PACKAGE = "bmad-method"
DEFAULT_BMAD_MODULES = "bmm,tea"
DEFAULT_BMAD_TOOLS = "claude-code"
BMAD_PIN_FILENAME = "bmad-pin.json"
PLANNING_ARTIFACTS_DIR = Path("_bmad-output") / "planning-artifacts"
IMPLEMENTATION_ARTIFACTS_DIR = Path("_bmad-output") / "implementation-artifacts"
_LEGACY_WORKFLOWS_DIR = Path("bmm") / "workflows"
_BMM_CONFIG = Path("bmm") / "config.yaml"
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
    if bmad_path.is_dir() and validate_bmad_layout(bmad_path, root):
        pinned_ref = _resolve_pinned_ref(root, bmad_path)
        _write_pin_file(
            root,
            install_method="validated",
            install_source=_submodule_url(root) or "local",
            pinned_ref=pinned_ref,
        )
        workflows = tuple(list_planning_workflows(bmad_path, root))
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="validated",
            pinned_ref=pinned_ref,
            planning_workflows=workflows,
            message="existing BMAD installation validated",
        )

    explicit_submodule = submodule_url or os.environ.get("RALPH_BMAD_SUBMODULE_URL")
    use_submodule = explicit_submodule is not None or os.environ.get("RALPH_BMAD_USE_SUBMODULE") == "1"
    if use_submodule and _is_git_repository(root):
        result = _integrate_bmad_submodule(root, bmad_path, submodule_url=explicit_submodule)
        if result.action != "failed":
            return result

    installer_result = _integrate_bmad_installer(root, bmad_path)
    if installer_result is not None:
        return installer_result

    if not _is_git_repository(root):
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="skipped",
            pinned_ref=None,
            planning_workflows=(),
            message=(
                "project is not a git repository; install BMAD with "
                f"`{bmad_install_hint(root)}`"
            ),
        )

    return BmadIntegrationResult(
        bmad_path=bmad_path,
        action="failed",
        pinned_ref=None,
        planning_workflows=(),
        message=_installer_failure_message(root),
    )


def ensure_planning_output_dirs(project_dir: str | Path) -> None:
    root = Path(project_dir).resolve()
    (root / PLANNING_ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)
    (root / IMPLEMENTATION_ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)


def validate_bmad_layout(bmad_dir: str | Path, project_dir: str | Path | None = None) -> bool:
    root = Path(bmad_dir)
    project = _resolve_project_dir(root, project_dir)
    if not (root / _BMM_CONFIG).is_file():
        return False
    if (root / _LEGACY_WORKFLOWS_DIR).is_dir():
        return True
    if (root / "core").is_dir():
        return True
    return _has_bmad_skills(project)


def list_planning_workflows(bmad_dir: str | Path, project_dir: str | Path | None = None) -> list[str]:
    root = Path(bmad_dir)
    project = _resolve_project_dir(root, project_dir)

    workflows_root = root / _LEGACY_WORKFLOWS_DIR
    if workflows_root.is_dir():
        discovered: list[str] = []
        for path in sorted(workflows_root.rglob("workflow.yaml")):
            relative = path.parent.relative_to(workflows_root).as_posix()
            lowered = relative.lower()
            if any(keyword in lowered for keyword in _PLANNING_WORKFLOW_KEYWORDS):
                discovered.append(relative)
        return discovered

    skills_dir = project / ".claude" / "skills"
    if not skills_dir.is_dir():
        return []

    discovered = []
    for path in sorted(skills_dir.iterdir()):
        if not path.is_dir() or not path.name.startswith("bmad-"):
            continue
        lowered = path.name.lower()
        if any(keyword in lowered for keyword in _PLANNING_WORKFLOW_KEYWORDS):
            discovered.append(path.name)
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


def bmad_install_hint(project_dir: str | Path | None = None) -> str:
    directory = "." if project_dir is None else str(Path(project_dir).resolve())
    modules = os.environ.get("RALPH_BMAD_MODULES", DEFAULT_BMAD_MODULES)
    tools = os.environ.get("RALPH_BMAD_TOOLS", DEFAULT_BMAD_TOOLS)
    package = _npm_package_spec()
    return (
        f"npx --yes {package} install "
        f"--directory {directory} --modules {modules} --tools {tools} --yes"
    )


def submodule_update_hint() -> str:
    return bmad_install_hint()


def _integrate_bmad_installer(root: Path, bmad_path: Path) -> BmadIntegrationResult | None:
    if shutil.which(_npx_command()) is None:
        return None

    result = _run_bmad_installer(root)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="failed",
            pinned_ref=None,
            planning_workflows=(),
            message=detail or "BMAD installer failed",
        )

    if not validate_bmad_layout(bmad_path, root):
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="failed",
            pinned_ref=None,
            planning_workflows=(),
            message="BMAD installer finished but required planning layout is missing",
        )

    pinned_ref = _read_bmm_version(bmad_path)
    _write_pin_file(
        root,
        install_method="npx",
        install_source=_npm_package_spec(),
        pinned_ref=pinned_ref,
    )
    workflows = tuple(list_planning_workflows(bmad_path, root))
    return BmadIntegrationResult(
        bmad_path=bmad_path,
        action="initialized",
        pinned_ref=pinned_ref,
        planning_workflows=workflows,
        message="BMAD installed via npx bmad-method",
    )


def _integrate_bmad_submodule(
    root: Path,
    bmad_path: Path,
    *,
    submodule_url: str | None,
) -> BmadIntegrationResult:
    url = submodule_url or DEFAULT_BMAD_SUBMODULE_URL
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

    if not validate_bmad_layout(bmad_path, root):
        return BmadIntegrationResult(
            bmad_path=bmad_path,
            action="failed",
            pinned_ref=None,
            planning_workflows=(),
            message=(
                "BMAD submodule added but required planning layout is missing; "
                f"run `{bmad_install_hint(root)}` instead of git submodule"
            ),
        )

    pinned_ref = _resolve_pinned_ref(root, bmad_path)
    _write_pin_file(
        root,
        install_method="submodule",
        install_source=url,
        pinned_ref=pinned_ref,
    )
    workflows = tuple(list_planning_workflows(bmad_path, root))
    return BmadIntegrationResult(
        bmad_path=bmad_path,
        action="initialized",
        pinned_ref=pinned_ref,
        planning_workflows=workflows,
        message="BMAD submodule configured",
    )


def _installer_failure_message(root: Path) -> str:
    if shutil.which(_npx_command()) is None:
        return (
            "Node.js/npx is required to install BMAD (v6+). "
            f"Install Node 20+, then run `{bmad_install_hint(root)}`"
        )
    return f"BMAD install failed; run `{bmad_install_hint(root)}` manually"


def _run_bmad_installer(project_dir: Path) -> subprocess.CompletedProcess[str]:
    modules = os.environ.get("RALPH_BMAD_MODULES", DEFAULT_BMAD_MODULES)
    tools = os.environ.get("RALPH_BMAD_TOOLS", DEFAULT_BMAD_TOOLS)
    command = [
        _npx_command(),
        "--yes",
        _npm_package_spec(),
        "install",
        "--directory",
        str(project_dir),
        "--modules",
        modules,
        "--tools",
        tools,
        "--yes",
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def _npm_package_spec() -> str:
    package = os.environ.get("RALPH_BMAD_NPM_PACKAGE", DEFAULT_BMAD_NPM_PACKAGE)
    channel = os.environ.get("RALPH_BMAD_INSTALL_CHANNEL", "").strip().lower()
    if channel == "next":
        return f"{package}@next"
    return package


def _npx_command() -> str:
    return "npx.cmd" if sys.platform == "win32" else "npx"


def _resolve_project_dir(bmad_dir: Path, project_dir: str | Path | None) -> Path:
    if project_dir is not None:
        return Path(project_dir).resolve()
    return bmad_dir.resolve().parent


def _has_bmad_skills(project_dir: Path) -> bool:
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.is_dir():
        return False
    return any(path.is_dir() and path.name.startswith("bmad-") for path in skills_dir.iterdir())


def _read_bmm_version(bmad_path: Path) -> str | None:
    config_path = bmad_path / _BMM_CONFIG
    if not config_path.is_file():
        return None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("version:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _write_pin_file(
    project_dir: Path,
    *,
    install_method: str,
    install_source: str,
    pinned_ref: str | None,
) -> None:
    pin_dir = project_dir / ".ralph"
    pin_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "path": BMAD_SUBMODULE_DIR,
        "install_method": install_method,
        "install_source": install_source,
        "ref": pinned_ref,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "update_command": bmad_install_hint(project_dir),
    }
    (pin_dir / BMAD_PIN_FILENAME).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resolve_pinned_ref(project_dir: Path, bmad_path: Path) -> str | None:
    submodule_ref = _submodule_ref(project_dir, bmad_path)
    if submodule_ref:
        return submodule_ref
    version = _read_bmm_version(bmad_path)
    if version:
        return version
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
