# Local publication gates — 2026-08-21

This directory records the accepted local replacement for the unavailable
hosted GitHub Actions runner. The pre-commit and `act` gates were run against
the same candidate tree before publication and are repeated from a clean,
detached checkout after commit.

## Environment

- pre-commit: `4.6.2`
- act: `0.2.89`
- Podman: `5.8.3`
- act runner: `docker.io/catthehacker/ubuntu:act-latest`
- local runner image ID: `10ca2cfc3a29b70e13fe0a2a9244fe7e5d24fbd7350ac4205028335c9541f926`
- act container network: `none`
- hosted Python control: `3.11`
- offline act Python: `3.12.3` with a workflow assertion of `>=3.11`

## Accepted gates

1. `PRE_COMMIT_COLOR=never pre-commit run --all-files --verbose`
2. `NO_COLOR=1 tools/run-act-local.sh`

See [pre-commit.log](pre-commit.log) and [act-offline.log](act-offline.log) for
the normalized output. Machine-local paths and routine container plumbing are
omitted; test counts, skips, step outcomes, image identity, Python version, and
manifest hashes are retained.

## Post-commit clean-clone verification

Commit `b40092f92800c11372e7af13dd1e59ed8f139564` was cloned locally with
independent Git metadata and verified before publication:

- pre-commit: all seven hooks passed; 43 unit tests passed with two skips;
- static analysis: zero errors, warnings, or informational findings;
- evidence: 48-artifact and 314-artifact manifests matched their retained
  SHA-256 values;
- act: the network-isolated job passed with Python 3.12.3, 43 unit tests, two
  skips, doctor, fixture tests, and shell syntax;
- repository status and Git object verification were clean.

## Rejected setup attempts

- The first wrapper invocation failed before workflow execution because act
  `0.2.89` does not accept `--no-colour`. The unsupported cosmetic flag was
  removed.
- The next workflow run passed with Python 3.11, but `setup-python` downloaded
  Python and pip. It proved workflow compatibility but was not accepted as the
  offline gate.
- The accepted run skips `setup-python` only when `ACT=true`, asserts the
  cached runner's Python satisfies the repository minimum, and creates the job
  container with `network=none`. Hosted GitHub Actions still uses the pinned
  Python 3.11 setup action.
- A later repeat initially could not reach the stopped Podman machine. Starting
  Podman and `act` in the same validation session restored the local API proxy;
  that infrastructure-only failure is rejected, and the subsequent green run
  is the retained result.
- A detached linked worktree passed pre-commit and evidence verification, but
  its act replay was rejected because act copied the worktree's `.git` pointer
  without the parent Git directory. The accepted post-commit replay used an
  independent local clone, preserving valid Git metadata inside the container.

## Defect caught by the real commit hook

The first actual commit attempt exposed that pre-commit's `GIT_INDEX_FILE`
override leaked into Highlander's nested trial repositories. That made a linked
worktree interpret the parent repository's `.git/index` as its own. Highlander
now strips Git's repository-routing environment variables at every nested Git
boundary, and a regression test runs a complete fake match with the override
present. The accepted gates include that test (43 total).
