# Contributing

Keep changes small, reviewable, and honest about what they establish. Highlander results are bound to the named harness versions, model route, task pack, controls, and run period; do not present a version-bound observation as a universal winner.

Before making claims about scope, execution, or evidence, review the [open problems inventory](docs/OPEN_PROBLEMS.md). For vulnerability reports and evidence-safe disclosure, see [Security policy](SECURITY.md).

## Local setup and gate

Use Python 3.11 or newer from the repository root. A minimal setup is:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip pre-commit
pre-commit install
```

Before opening a PR, validate the included match without executing a harness or making model calls:

```sh
python3 tools/highlander.py doctor examples/matches/fake-t001.json
```

Run the complete local gate:

```sh
pre-commit run --all-files --verbose
```

## Pull requests

- Keep the PR focused and explain the behavior or documentation change.
- Report the commands run and their results; link retained evidence when applicable.
- Keep real credentials, private data, and unapproved live execution out of commits and evidence (see [Security policy](SECURITY.md#keep-reports-and-evidence-safe)).
- Preserve invalid, blocked, and incomplete outcomes rather than hiding them.

## Evidence

Evidence is the inspectable record of what happened: commands, diffs, tests, evaluator output, manifests, and paths to retained artifacts. Evidence may show an invalid, blocked, or incomplete attempt; keep those outcomes visible. A change is done when the applicable checks and acceptance criteria pass, and a confident summary is not evidence by itself.
