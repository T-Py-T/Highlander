# Local publication gates — 2026-08-22

This directory records the accepted local gates for the Atomic adapter,
hard-first season, and per-task leaderboard. No model call was made.

## Environment

- pre-commit: `4.6.2`
- act: `0.2.89`
- Podman: `5.8.3`
- act runner: `docker.io/catthehacker/ubuntu:act-latest`
- local runner image ID: `cb041d0df9a749a73358ded823dd44f7c24111ef3efd152a3e6f3f4e3846f153`
- act container network: `none`
- offline act Python: `3.12.3`, asserted to satisfy Python `>=3.11`

## Accepted gates

1. Full clean-room image build and seven-image digest doctor.
2. Six-Harness no-auth Match doctor.
3. `python3 -m unittest discover -s tests`.
4. `pyright highlander tests`.
5. `pre-commit run --all-files --verbose`.
6. `tools/run-act-local.sh` with the job container network disabled.

See [clean-room.log](clean-room.log), [pre-commit.log](pre-commit.log), and
[act-offline.log](act-offline.log) for normalized output.

## Protocol boundary

- The previous result visual is one HarnessBench task repeated three times.
- The new draft season is nine unchanged coding/DevOps tasks, six Harnesses,
  and three attempts per Harness/task cell.
- `Overall` is the mean of the per-task means. Per-task mean and worst–best
  range are mandatory; best-of-three is a separate capability view.
- OMP is the current control. NanoBot and every other lane with a missing
  dedicated seed remain unavailable, never zero.
- No performance rank exists until scored evidence is appended.

## Rejected setup attempts

- The first Atomic image copied only the release launcher. Qualification
  exposed a missing `app.js`; the accepted image installs the complete
  checksum-verified release bundle and reports `0.9.15`.
- The first seven-image rebuild was interrupted after a Hermes clone made no
  progress for several bounded intervals. No lock was written. A subsequent
  exact-commit Hermes build succeeded, and the complete cached rebuild plus
  digest doctor then passed.
- The first auth-gate summary command used zsh's reserved `status` variable and
  failed after generating the Match. The accepted rerun used a task-specific
  variable and showed all six clean-room seeds unavailable.
