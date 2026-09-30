# Hireability and evidence map

This page orients staffing readers to inspectable engineering choices in Highlander. It is stewardship and evidence documentation, not an acceptance gate, scorecard, release declaration, or claim that any work is complete or `READY`.

For repository setup, local gates, and contribution rules, see [Contributing](../CONTRIBUTING.md). For the public entry point and quick demo commands, see [README](../README.md).

## What this proves

Highlander is a working example of controlled evaluation infrastructure:

- **Experimental discipline:** it compares harnesses with the repository commit, models, task packet, evaluator, limits, and permissions held fixed—not a model swap presented as a harness result.
- **Reproducible operations:** it schedules isolated trials and retains the transcript, tool ledger, diff, tests, evaluator output, usage observations, operator interactions, and evidence paths for inspection.
- **Safe execution boundaries:** `run` is a dry run by default; `--execute` is explicit, and real runs use the disposable clean-room path with separate credentials and cost approval.
- **Honest reporting:** invalid attempts remain visible, while results stay scoped to the named harness versions, model route, task pack, controls, and run period. Dispersion is reported rather than collapsed into a universal winner claim.

## Evidence trail

| Signal | Where to verify it |
|---|---|
| Controlled experiment design | [Gauntlet design](GAUNTLET.md) and [leaderboard contract](LEADERBOARD.md) |
| Safe, repeatable execution | [Match runner](MATCH-RUNNER.md) and [clean-room execution](CLEAN-ROOM.md) |
| Evidence capture and redaction | [Evidence contract](EVIDENCE.md), including manifest verification |
| Honest handling of invalid or incomplete runs | [Current result](../README.md#current-result) and [open problems inventory](OPEN_PROBLEMS.md) |
| Maintainer judgment and collaboration | [Contributing](../CONTRIBUTING.md), [support guidance](../SUPPORT.md), and [Code of Conduct](../CODE_OF_CONDUCT.md) |

These links are an evidence trail for how the system is built and operated; the [open problems inventory](OPEN_PROBLEMS.md) keeps unresolved limits visible and defines the [tip-cite protocol](OPEN_PROBLEMS.md#tip-cite-protocol). Neither is a claim of production readiness or a substitute for the stated limits.

## Evidence is not `READY`

Evidence is the inspectable record of commands, diffs, tests, evaluator output, manifests, and retained artifact paths. It may document a valid result, an invalid attempt, a blocked path, or incomplete work. `READY` is a separate status that requires the applicable checks and acceptance criteria to pass. A tip-cite, confident summary, or untested or blocked work is never `READY`.

## Tip-cite bank

Tip-cite bank base pending merge on `main` + this PR pending Steward; Steward resolves after merge; provenance only; never READY.

When recording a merged documentation change, use:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

Use the first eight hexadecimal characters of the merge commit on `main` and the actual pull-request number. Resolve both only after the pull request exists and is merged. Never use a branch tip, invent or pad a tip, invent a PR number, or reuse an older cite. A tip-cite records provenance only; it never establishes `READY`.

See [Contributing](../CONTRIBUTING.md#tip-cite-bank) and the [open problems tip-cite protocol](OPEN_PROBLEMS.md#tip-cite-protocol) for the shared steward procedure.

## Honesty footer

This page reports inspectable evidence boundaries and version-bound observations; it does not establish production readiness, a universal winner, completion, or a score. Open problems and unknowns remain open until the applicable checks, approvals, and retained evidence exist.
