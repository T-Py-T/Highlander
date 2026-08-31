#!/usr/bin/env python3
"""Freeze, qualify, and run Highlander's disposable HarnessBench season."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.hb_season_run import doctor, execute_stage, freeze_protocol, qualify


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--manifest", required=True, type=Path)
    freeze.add_argument("--upstream", required=True, type=Path)
    freeze.add_argument("--image-lock", default=ROOT / ".highlander/images.lock.json", type=Path)
    freeze.add_argument("--output", required=True, type=Path)
    freeze.add_argument("--schedule-seed", default=56001, type=int)
    for name in ("doctor", "qualify", "run"):
        command = sub.add_parser(name)
        command.add_argument("--protocol", required=True, type=Path)
        command.add_argument("--protocol-sha256", required=True, type=Path)
        command.add_argument("--upstream", required=True, type=Path)
        if name == "qualify":
            command.add_argument("--output-root", default=ROOT / ".highlander/qualifications", type=Path)
        if name == "run":
            command.add_argument("--manifest", required=True, type=Path)
            command.add_argument("--qualification-root", default=ROOT / ".highlander/qualifications", type=Path)
            command.add_argument("--output-root", default=ROOT / ".highlander/runs", type=Path)
            command.add_argument("--stage")
            command.add_argument("--max-trials", type=int)
            command.add_argument("--retry-invalid", action="store_true")
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze_protocol(
            root=ROOT,
            manifest_path=args.manifest,
            upstream=args.upstream,
            image_lock_path=args.image_lock,
            output=args.output,
            schedule_seed=args.schedule_seed,
        )
    elif args.command == "doctor":
        result = doctor(args.protocol, args.protocol_sha256, args.upstream, ROOT)
    elif args.command == "qualify":
        result = qualify(args.protocol, args.protocol_sha256, args.upstream, ROOT, args.output_root)
    else:
        result = execute_stage(
            protocol_path=args.protocol,
            sidecar_path=args.protocol_sha256,
            manifest_path=args.manifest,
            upstream=args.upstream,
            root=ROOT,
            qualification_root=args.qualification_root,
            output_root=args.output_root,
            stage_id=args.stage,
            max_trials=args.max_trials,
            retry_invalid=args.retry_invalid,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
