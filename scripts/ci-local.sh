#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repository_root"

if command -v python >/dev/null 2>&1; then
  python_bin=python
else
  python_bin=python3
fi

"$python_bin" -m unittest discover -s tests

"$python_bin" -m compileall -q highlander tools
"$python_bin" tools/highlander.py doctor examples/matches/fake-t001.json

"$python_bin" -m unittest discover -s fixtures/job-runner -p 'test_*.py'

bash -n tools/prepare-run.sh tools/run-act-local.sh containers/base/highlander-entrypoint

"$python_bin" tools/evidence-bundle.py verify results/fake-t002-protocol-r1
"$python_bin" tools/hb-evidence.py verify results/hb-devhard-043-gpt54-medium-host4-r1
"$python_bin" tools/hb-evidence.py verify-season results/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4
"$python_bin" tools/hb-evidence.py verify-season results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1
