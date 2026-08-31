#!/usr/bin/env python3
"""Export or verify sanitized HarnessBench pilot and season evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.hb_evidence import (  # noqa: E402
    PilotEvidenceError,
    export_pilot_bundle,
    export_season_bundle,
    verify_pilot_bundle,
    verify_season_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--source", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--runner-repository", default=str(ROOT))
    verify = sub.add_parser("verify")
    verify.add_argument("bundle")
    export_season = sub.add_parser("export-season")
    export_season.add_argument("--source", required=True)
    export_season.add_argument("--output", required=True)
    export_season.add_argument("--runner-repository", default=str(ROOT))
    verify_season = sub.add_parser("verify-season")
    verify_season.add_argument("bundle")
    args = parser.parse_args()
    try:
        if args.command == "export":
            result = export_pilot_bundle(
                args.source, args.output, args.runner_repository
            )
        elif args.command == "verify":
            result = verify_pilot_bundle(args.bundle)
        elif args.command == "export-season":
            result = export_season_bundle(
                args.source, args.output, args.runner_repository
            )
        else:
            result = verify_season_bundle(args.bundle)
    except PilotEvidenceError as exc:
        print(f"HarnessBench pilot evidence: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
