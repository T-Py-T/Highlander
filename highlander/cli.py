"""Dependency-free Highlander command-line interface."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .engine import MatchRunner, atomic_json, canonical_json, run_worker
from .model import HighlanderError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="highlander")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="read-only adapter preflight")
    doctor.add_argument("match")
    doctor.add_argument("--session", choices=["headless", "tmux"])

    run = subparsers.add_parser("run", help="plan by default; execute explicitly")
    run.add_argument("match")
    run.add_argument("--session", choices=["headless", "tmux"])
    run.add_argument(
        "--execute",
        action="store_true",
        help="create worktrees and run workers; omitted means dry-run",
    )
    run.add_argument(
        "--save-plan",
        help="write the reviewed dry-run plan to this path",
    )
    run.add_argument(
        "--plan",
        help="execute this exact previously saved plan (required with --execute)",
    )

    status = subparsers.add_parser("status", help="read retained Match state")
    status.add_argument("run_directory")

    stop = subparsers.add_parser("stop", help="stop an active tmux Match session")
    stop.add_argument("run_directory")

    worker = subparsers.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--trial-plan", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            runner = MatchRunner.from_file(args.match)
            print(canonical_json(runner.doctor(session_override=args.session)), end="")
            return 0
        if args.command == "run":
            runner = MatchRunner.from_file(args.match)
            if args.execute:
                if args.save_plan:
                    raise HighlanderError(
                        "--save-plan cannot be combined with --execute"
                    )
                if not args.plan:
                    raise HighlanderError(
                        "--execute requires --plan with the exact reviewed dry-run plan"
                    )
                reviewed_plan = json.loads(
                    Path(args.plan).expanduser().read_text(encoding="utf-8")
                )
                result = runner.execute(
                    reviewed_plan=reviewed_plan,
                    session_override=args.session,
                )
            else:
                if args.plan:
                    raise HighlanderError("--plan is valid only with --execute")
                result = runner.plan(session_override=args.session)
                if args.save_plan:
                    atomic_json(Path(args.save_plan).expanduser().resolve(), result)
            print(canonical_json(result), end="")
            return 0
        if args.command == "status":
            print(
                canonical_json(_status_without_spec(Path(args.run_directory))), end=""
            )
            return 0
        if args.command == "stop":
            print(canonical_json(_stop_tmux(Path(args.run_directory))), end="")
            return 0
        if args.command == "_worker":
            return run_worker(args.trial_plan)
    except HighlanderError as exc:
        print(f"Highlander: {exc}", file=sys.stderr)
        return 2
    return 2


def _status_without_spec(run_dir: Path) -> dict:
    root = run_dir.expanduser().resolve()
    result = root / "match-result.json"
    if result.is_file():
        return json.loads(result.read_text(encoding="utf-8"))
    journal = root / "journal" / "match-events.jsonl"
    if not journal.is_file():
        raise HighlanderError(f"Not a Highlander Match directory: {root}")
    lines = journal.read_text(encoding="utf-8").splitlines()
    last = json.loads(lines[-1]) if lines else None
    return {"match_id": root.name, "state": last["event"] if last else "UNKNOWN", "last_event": last}


def _stop_tmux(run_dir: Path) -> dict:
    root = run_dir.expanduser().resolve()
    manifest_path = root / "session" / "manifest.json"
    if not manifest_path.is_file():
        raise HighlanderError(f"Session manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("adapter") != "tmux" or not manifest.get("tmux_session"):
        raise HighlanderError(
            "stop currently supports tmux Matches only; foreground headless runs stop with their controller"
        )
    binary = shutil.which("tmux")
    if not binary:
        raise HighlanderError("tmux is not installed")
    session = manifest["tmux_session"]
    if not session.startswith("highlander-"):
        raise HighlanderError("refusing to stop a session without a Highlander name")
    expected_match = manifest.get("match_id")
    if not isinstance(expected_match, str) or expected_match != root.name:
        raise HighlanderError("session manifest Match identity does not match its directory")
    exists = subprocess.run(
        [binary, "has-session", "-t", session],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if not exists:
        return {
            "match_directory": str(root),
            "tmux_session": session,
            "stopped": False,
            "already_absent": True,
        }
    marker = subprocess.run(
        [binary, "show-options", "-v", "-t", session, "@highlander_match_id"],
        capture_output=True,
        text=True,
        check=False,
    )
    if marker.returncode != 0 or marker.stdout.strip() != expected_match:
        raise HighlanderError(
            "refusing to stop a tmux session without the matching Highlander ownership marker"
        )
    result = subprocess.run(
        [binary, "kill-session", "-t", session],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "match_directory": str(root),
        "tmux_session": session,
        "stopped": result.returncode == 0,
        "already_absent": False,
    }
