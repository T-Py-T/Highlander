#!/usr/bin/env python3
"""HarnessBench generic_cli bridge into Highlander's disposable images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.hb_clean import SUPPORTED_HARNESSES, execute_clean_adapter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--harness", choices=SUPPORTED_HARNESSES, required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--trial-id", required=True)
    args = parser.parse_args()
    protocol = json.loads(Path(args.protocol).resolve().read_text(encoding="utf-8"))
    return execute_clean_adapter(
        protocol=protocol,
        harness_id=args.harness,
        workspace=Path(args.workspace),
        prompt_file=Path(args.prompt_file),
        evidence_dir=Path(args.evidence_dir),
        trial_id=args.trial_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
