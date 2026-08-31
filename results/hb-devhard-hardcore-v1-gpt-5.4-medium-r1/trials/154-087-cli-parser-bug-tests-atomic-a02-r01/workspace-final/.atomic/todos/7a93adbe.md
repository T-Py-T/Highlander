{
  "id": "7a93adbe",
  "title": "Fix csvtool CLI parsing/filter/sort bugs and add regression tests",
  "tags": [
    "bugfix",
    "tests",
    "csv",
    "cli"
  ],
  "status": "completed",
  "created_at": "2026-08-31T18:39:36.691Z"
}

Fixed csvtool CLI to use Python's csv module for parsing/writing, support repeated --where with AND semantics, support descending sort tokens like `--sort -field`, sort numeric-looking values numerically, preserve headers on empty results, and raise clear non-zero CLI errors for bad/missing fields. Added focused regression tests in tests/test_cli_regression.py. Note: the exact `python -m pytest tests` command could not run here because this environment has no `python` alias and no `pytest` installed; I validated the full test suite by directly executing all test functions under python3, and all passed.
