#!/usr/bin/env python3
"""HarnessBench generic_cli bridge for Highlander's host-isolated pilot."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.hb_pilot import SUPPORTED_HARNESSES, execute_host_harness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", required=True, choices=SUPPORTED_HARNESSES)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--timeout-seconds", required=True, type=int)
    args = parser.parse_args()
    profile_root = os.environ.get("HIGHLANDER_PILOT_PROFILE_ROOT")
    if not profile_root:
        parser.error("HIGHLANDER_PILOT_PROFILE_ROOT is required")
    try:
        return execute_host_harness(
            args.harness,
            workspace=args.workspace,
            prompt_file=args.prompt_file,
            evidence_dir=args.evidence_dir,
            profile_root=Path(profile_root),
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, ValueError) as exc:
        print(f"highlander host adapter unavailable: {exc}", file=sys.stderr)
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
