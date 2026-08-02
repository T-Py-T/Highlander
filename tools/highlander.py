#!/usr/bin/env python3
"""Run Highlander from a source checkout without installing it."""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from highlander.cli import main  # noqa: E402


raise SystemExit(main())
