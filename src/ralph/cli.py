from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="Autonomous SDLC pipeline runner",
    )
    parser.add_argument("--version", "-V", action="version", version=f"ralph {__version__}")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-essential output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show additional detail")

    subcommands = parser.add_subparsers(dest="command", metavar="COMMAND")

    start = subcommands.add_parser("start", help="Start the Ralph daemon", description="Start the Ralph daemon")
    start.set_defaults(handler=_run_start)

    stop = subcommands.add_parser("stop", help="Stop the Ralph daemon", description="Stop the Ralph daemon")
    stop.set_defaults(handler=_run_stop)

    status = subcommands.add_parser("status", help="Query pipeline status", description="Query pipeline status")
    status.add_argument("--detail", action="store_true", help="Show story and worker details")
    status.set_defaults(handler=_run_status)

    diagnose = subcommands.add_parser(
        "diagnose",
        help="Generate diagnostic report for a story",
        description="Generate diagnostic report for a story",
    )
    diagnose.add_argument("story_id", metavar="STORY_ID", type=_story_id)
    diagnose.set_defaults(handler=_run_diagnose)

    retry = subcommands.add_parser(
        "retry",
        help="Re-feed a story into the pipeline",
        description="Re-feed a story into the pipeline",
    )
    retry.add_argument("story_id", metavar="STORY_ID", type=_story_id)
    retry.set_defaults(handler=_run_retry)

    init = subcommands.add_parser("init", help="Initialize Ralph on a project", description="Initialize Ralph on a project")
    init.set_defaults(handler=_run_init)

    watch = subcommands.add_parser(
        "watch",
        help="Live TUI monitoring dashboard",
        description="Live TUI monitoring dashboard",
    )
    watch.set_defaults(handler=_run_watch)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    handler(args)
    return 0


def _story_id(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("invalid value: expected numeric STORY_ID") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("invalid value: STORY_ID must be positive")
    return parsed


def _run_start(_args: argparse.Namespace) -> None:
    print("start: not yet implemented")


def _run_stop(_args: argparse.Namespace) -> None:
    print("stop: not yet implemented")


def _run_status(args: argparse.Namespace) -> None:
    suffix = " with detail" if args.detail else ""
    print(f"status: not yet implemented{suffix}")


def _run_diagnose(args: argparse.Namespace) -> None:
    print(f"diagnose: not yet implemented for story {args.story_id}")


def _run_retry(args: argparse.Namespace) -> None:
    print(f"retry: not yet implemented for story {args.story_id}")


def _run_init(_args: argparse.Namespace) -> None:
    print("init: not yet implemented")


def _run_watch(_args: argparse.Namespace) -> None:
    print("watch: not yet implemented")
