#!/usr/bin/env python3
"""Export or verify a sanitized Highlander evidence bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.evidence import (  # noqa: E402
    EvidenceExportError,
    export_public_bundle,
    verify_public_bundle,
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="evidence-bundle.py")
    commands = value.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--source", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--runner-repository", default=str(ROOT))
    verify = commands.add_parser("verify")
    verify.add_argument("bundle")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "export":
            result = export_public_bundle(
                args.source, args.output, args.runner_repository
            )
        else:
            result = verify_public_bundle(args.bundle)
    except EvidenceExportError as exc:
        print(f"Evidence bundle: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
