#!/usr/bin/env python3
"""Run the frozen r4 CLI with a post-score evidence-copy-only correction.

The frozen controller used shutil.copytree's default symlink-following mode for
workspace-final. Some valid task workspaces contain virtual-environment links to
host interpreters. Preserve those links only when retaining workspace-final;
all model-facing and scoring paths continue through the frozen implementation.
"""

from __future__ import annotations

import runpy
import shutil
import sys
from pathlib import Path
from typing import Any


ORIGINAL_COPYTREE = shutil.copytree


def evidence_copytree(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
    """Preserve symlinks only for Highlander's final-workspace evidence copy."""

    if Path(dst).name == "workspace-final":
        if "symlinks" in kwargs and kwargs["symlinks"] is not False:
            raise ValueError("unexpected preconfigured symlink policy")
        kwargs["symlinks"] = True
    return ORIGINAL_COPYTREE(src, dst, *args, **kwargs)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: symlink-preserving-workspace-copy.py <hb-season arguments>")
    shutil.copytree = evidence_copytree
    runpy.run_path("tools/hb-season.py", run_name="__main__")


if __name__ == "__main__":
    main()
