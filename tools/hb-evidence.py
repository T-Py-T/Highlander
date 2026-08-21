#!/usr/bin/env python3
"""Export or verify a sanitized HarnessBench pilot evidence bundle."""

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
    verify_pilot_bundle,
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
    args = parser.parse_args()
    try:
        if args.command == "export":
            result = export_pilot_bundle(
                args.source, args.output, args.runner_repository
            )
        else:
            result = verify_pilot_bundle(args.bundle)
    except PilotEvidenceError as exc:
        print(f"HarnessBench pilot evidence: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
