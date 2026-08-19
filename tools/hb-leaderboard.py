#!/usr/bin/env python3
"""Build a deterministic Highlander season leaderboard from JSONL evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.season import (  # noqa: E402
    SeasonError,
    aggregate_season,
    leaderboard_markdown,
    load_jsonl,
    load_manifest,
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="hb-leaderboard.py")
    value.add_argument("--manifest", required=True)
    value.add_argument("--results", required=True)
    value.add_argument("--format", choices=("json", "markdown"), default="markdown")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        summary = aggregate_season(
            load_manifest(args.manifest), load_jsonl(args.results)
        )
    except SeasonError as exc:
        print(f"Leaderboard: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(leaderboard_markdown(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
