from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .common.protocol import Request
from .config import RalphConfig, default_project_config_path, default_user_config_path, resolve_config
from .daemon import RuntimePaths, read_status, request_daemon, run_daemon, start_daemon, stop_daemon
from .init_project import init_project
from .common.db import StateStore
from .pipeline.artifact import ArtifactParseError, SprintPlanNotFoundError
from .pipeline.ingestion import ingest_sprint_plan, persist_ingested_plan
from .render import Spinner, error_message, resolve_theme, section_border
from .render.theme import Semantic
from .diagnose import (
    DiagnoseLoadError,
    DiagnoseLoadErrorKind,
    list_failed_story_ids,
    load_diagnose_snapshot,
    render_diagnose,
)
from .retry import RetryError, RetryErrorKind, render_retry_confirmation, retry_story
from .status import load_status_snapshot, render_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="Autonomous SDLC pipeline runner",
    )
    parser.add_argument("--version", "-V", action="version", version=f"ralph {__version__}")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show additional detail")
    parser.add_argument("--config", type=Path, help="Project config path")
    parser.add_argument("--user-config", type=Path, help="User config path")
    parser.add_argument("--max-workers", type=_positive_int, help="Override configured worker limit")

    subcommands = parser.add_subparsers(dest="command", metavar="COMMAND")

    start = subcommands.add_parser("start", help="Start the Ralph daemon", description="Start the Ralph daemon")
    _add_project_dir_arg(start)
    start.set_defaults(handler=_run_start)

    stop = subcommands.add_parser("stop", help="Stop the Ralph daemon", description="Stop the Ralph daemon")
    _add_project_dir_arg(stop)
    stop.set_defaults(handler=_run_stop)

    status = subcommands.add_parser("status", help="Query pipeline status", description="Query pipeline status")
    _add_project_dir_arg(status)
    status.add_argument("--detail", action="store_true", help="Show story and worker details")
    status.set_defaults(handler=_run_status)

    diagnose = subcommands.add_parser(
        "diagnose",
        help="Generate diagnostic report for a story",
        description="Generate diagnostic report for a story",
    )
    _add_project_dir_arg(diagnose)
    diagnose.add_argument("story_id", metavar="STORY_ID", nargs="?", type=_story_id)
    diagnose.set_defaults(handler=_run_diagnose)

    retry = subcommands.add_parser(
        "retry",
        help="Re-feed a story into the pipeline",
        description="Re-feed a story into the pipeline",
    )
    _add_project_dir_arg(retry)
    retry.add_argument("story_id", metavar="STORY_ID", type=_story_id)
    retry.set_defaults(handler=_run_retry)

    init = subcommands.add_parser("init", help="Initialize Ralph on a project", description="Initialize Ralph on a project")
    init.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Project directory to initialize")
    init.add_argument("--force", action="store_true", help="Overwrite existing ralph.toml")
    init.set_defaults(handler=_run_init)

    watch = subcommands.add_parser(
        "watch",
        help="Live TUI monitoring dashboard",
        description="Live TUI monitoring dashboard",
    )
    watch.set_defaults(handler=_run_watch)

    completions = subcommands.add_parser(
        "completions",
        help="Generate shell completions",
        description="Generate shell completions",
    )
    completions.add_argument("shell", choices=["bash", "zsh", "fish"], help="Shell to generate completions for")
    completions.set_defaults(handler=_run_completions)

    daemon = subcommands.add_parser("_daemon", help=argparse.SUPPRESS)
    daemon.add_argument("--project-dir", type=Path, required=True)
    daemon.add_argument("--max-workers", type=_positive_int, required=True)
    daemon.set_defaults(handler=_run_daemon)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.theme = resolve_theme(no_color=args.no_color)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    handler(args)
    return 0


def _story_id(value: str) -> int:
    return _positive_int(value, label="STORY_ID")


def _positive_int(value: str, *, label: str = "value") -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid value: expected numeric {label}") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"invalid value: {label} must be positive")
    return parsed


def _add_project_dir_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Project directory")


def _resolved_config(args: argparse.Namespace) -> RalphConfig:
    project_dir = getattr(args, "project_dir", None) or Path.cwd()
    project_config = args.config or default_project_config_path(project_dir)
    user_config = args.user_config or default_user_config_path()
    overrides = RalphConfig(max_workers=args.max_workers)
    return resolve_config(
        user_config_path=user_config,
        project_config_path=project_config,
        overrides=overrides,
    )


def _run_start(args: argparse.Namespace) -> None:
    config = _resolved_config(args)
    init_project(args.project_dir, max_workers=config.max_workers or 5)
    try:
        ingestion = ingest_sprint_plan(args.project_dir)
    except SprintPlanNotFoundError as exc:
        print(
            error_message(
                "No sprint plan found in project",
                detail_lines=[
                    "Ralph looks for sprint plans in _bmad-output/implementation-artifacts/",
                    exc.guidance,
                ],
                suggestion="Run BMAD sprint planning first, then try ralph start again.",
                theme=args.theme,
            )
        )
        raise SystemExit(1) from exc
    except ArtifactParseError as exc:
        print(
            error_message(
                f"Failed to parse sprint plan ({exc.path})",
                detail_lines=[exc.detail],
                suggestion="Fix the artifact file or re-run BMAD sprint planning.",
                theme=args.theme,
            )
        )
        raise SystemExit(1) from exc

    paths = RuntimePaths(args.project_dir.resolve())
    paths.ensure()
    store = StateStore.open(paths.database_file)
    try:
        persist_ingested_plan(store, ingestion)
    finally:
        store.close()

    with Spinner("Starting daemon", theme=args.theme):
        status = start_daemon(args.project_dir, config)

    context_semantic = Semantic.ACTIVE if status.state == "starting" else Semantic.HEALTHY
    print(
        section_border(
            "Ralph",
            context=status.state,
            context_semantic=context_semantic,
            theme=args.theme,
        )
    )
    print(
        f"  sprint plan: {args.theme.bold(str(ingestion.story_count))} stories, "
        f"{args.theme.bold(str(ingestion.dependency_count))} dependencies"
    )
    print(
        f"  pid={args.theme.bold(str(status.pid))} "
        f"max_workers={args.theme.bold(str(status.max_workers))}"
    )


def _run_stop(args: argparse.Namespace) -> None:
    with Spinner("Stopping daemon", theme=args.theme):
        status = stop_daemon(args.project_dir)
    print(
        section_border(
            "Ralph",
            context=status.state,
            context_semantic=Semantic.SECONDARY if status.state == "stopped" else Semantic.ACTIVE,
            theme=args.theme,
        )
    )
    print(f"  pid={args.theme.dim(str(status.pid))}")


def _run_status(args: argparse.Namespace) -> None:
    paths = RuntimePaths(args.project_dir.resolve())
    snapshot = load_status_snapshot(paths.project_dir, detail=args.detail)
    if snapshot is None:
        print(
            error_message(
                "No running daemon found",
                suggestion="Start Ralph first: ralph start",
                theme=args.theme,
            )
        )
        raise SystemExit(1)

    print(
        render_status(
            snapshot,
            theme=args.theme,
            project_dir=paths.project_dir,
            detail=args.detail,
        )
    )


def _run_diagnose(args: argparse.Namespace) -> None:
    project_dir = getattr(args, "project_dir", Path.cwd())
    if args.story_id is None:
        failed_ids = list_failed_story_ids(project_dir)
        if not failed_ids:
            print("No failed stories to diagnose. All stories completed successfully.")
            return
        for story_id in failed_ids:
            _render_diagnose_for_story(project_dir, story_id, theme=args.theme)
            print()
        return

    _render_diagnose_for_story(project_dir, args.story_id, theme=args.theme)


def _render_diagnose_for_story(project_dir: Path, story_id: int, *, theme) -> None:
    result = load_diagnose_snapshot(project_dir, story_id)
    if isinstance(result, DiagnoseLoadError):
        if result.kind == DiagnoseLoadErrorKind.STORY_NOT_FOUND:
            print(
                error_message(
                    f"Story #{story_id} not found in current sprint",
                    suggestion="Run ralph status to see available stories",
                    theme=theme,
                )
            )
            raise SystemExit(1)
        return
    print(render_diagnose(result, theme=theme))


def _run_retry(args: argparse.Namespace) -> None:
    project_dir = getattr(args, "project_dir", Path.cwd())
    result = retry_story(project_dir, args.story_id)
    if isinstance(result, RetryError):
        if result.kind == RetryErrorKind.NO_DAEMON:
            print(
                error_message(
                    "No running daemon found",
                    suggestion="Start Ralph first: ralph start",
                    theme=args.theme,
                )
            )
            raise SystemExit(1)
        if result.kind == RetryErrorKind.STORY_NOT_FOUND:
            print(
                error_message(
                    f"Story #{args.story_id} not found in current sprint",
                    suggestion="Run ralph status to see available stories",
                    theme=args.theme,
                )
            )
            raise SystemExit(1)
        if result.kind == RetryErrorKind.INVALID_STATE:
            print(
                error_message(
                    (
                        f"Story #{args.story_id} is currently {result.state_label} "
                        "— retry is only available for failed stories"
                    ),
                    suggestion="Run ralph status to see available stories",
                    theme=args.theme,
                )
            )
            raise SystemExit(1)
        return
    print(render_retry_confirmation(result, theme=args.theme))


def _run_init(args: argparse.Namespace) -> None:
    max_workers = args.max_workers or 5
    result = init_project(args.project_dir, max_workers=max_workers, force=args.force)
    action = "created" if result.created_config else "kept"
    print(f"init: {action} {result.config_path}")
    print(f"init: ready {result.runtime_dir}")
    if result.bmad is not None:
        print(f"init: bmad {result.bmad.action} ({result.bmad.message})")
        if result.bmad.pinned_ref:
            print(f"init: bmad pinned ref {result.bmad.pinned_ref[:12]}")
        if result.bmad.planning_workflows:
            print(f"init: planning workflows available ({len(result.bmad.planning_workflows)})")
            print("init: use BMAD workflows in _bmad/bmm/workflows for PRD, architecture, UX, and sprint planning")
        print(f"init: update BMAD with `{_bmad_update_hint()}`")


def _bmad_update_hint() -> str:
    from .planning import submodule_update_hint

    return submodule_update_hint()


def _run_watch(_args: argparse.Namespace) -> None:
    print("watch: not yet implemented")


def _run_completions(args: argparse.Namespace) -> None:
    print(generate_completion(args.shell))


def _run_daemon(args: argparse.Namespace) -> None:
    raise SystemExit(run_daemon(args.project_dir, RalphConfig(max_workers=args.max_workers)))


def _status_from_response(data: dict[str, object]):
    from .daemon import DaemonStatus

    return DaemonStatus(
        state=str(data.get("state", "unknown")),
        pid=data.get("pid") if isinstance(data.get("pid"), int) else None,
        project_dir=str(data.get("project_dir", "")),
        max_workers=int(data.get("max_workers", 5)),
        started_at=data.get("started_at") if isinstance(data.get("started_at"), str) else None,
        heartbeat_at=data.get("heartbeat_at") if isinstance(data.get("heartbeat_at"), str) else None,
        message=str(data.get("message", "")),
    )


def generate_completion(shell: str) -> str:
    commands = "start stop status diagnose retry init watch completions"
    if shell == "bash":
        return f"""_ralph_complete()
{{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    COMPREPLY=( $(compgen -W "{commands}" -- "$cur") )
}}
complete -F _ralph_complete ralph"""
    if shell == "zsh":
        return f"""#compdef ralph
_arguments '1:command:({commands})'"""
    if shell == "fish":
        return "\n".join(f"complete -c ralph -f -a {command}" for command in commands.split())
    raise ValueError(f"unsupported shell: {shell}")
