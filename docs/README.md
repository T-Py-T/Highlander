# Documentation index

The `/docs` tree holds Highlander design contracts, runbooks, inventories, and architecture decision records. These pages explain how matches are controlled, executed, scored, and retained; they are stewardship and evidence documents, not acceptance gates, scorecards, release declarations, or claims that any work is complete or `READY`.

For contributor setup, local gates, and tip-cite rules, see [Contributing](../CONTRIBUTING.md). For vulnerability reports and evidence-safe reporting, see [Security policy](../SECURITY.md). For maintainer contact and stewardship boundaries, see [Maintainers](../MAINTAINERS.md).

## Design and operations

| Document | Purpose |
|---|---|
| [Gauntlet design](GAUNTLET.md) | Comparison rules and scoring model |
| [Match runner](MATCH-RUNNER.md) | CLI, state machine, adapters, and tmux workflow |
| [Clean-room execution](CLEAN-ROOM.md) | Disposable images, isolated homes, authentication seeds, and cleanup |
| [Leaderboard contract](LEADERBOARD.md) | Ranking, reliability, and invalid-run handling |
| [Season runbook](SEASON-RUNBOOK.md) | Qualification, execution, export, and verification steps |
| [Evidence contract](EVIDENCE.md) | Public bundles, redaction, and manifest verification |
| [Mobile supervision](MOBILE-SUPERVISION.md) | Observe-and-respond experiments |

## Inventories and decisions

| Document | Purpose |
|---|---|
| [Open problems inventory](OPEN_PROBLEMS.md) | Unresolved scope, execution, evidence, and stewardship questions |
| [Architecture decision records](adr/README.md) | Planning decisions, trade-offs, and architectural boundaries |

Individual pages report inspectable evidence boundaries and version-bound observations. They do not establish production readiness, a universal winner, or completion when work is open, blocked, invalid, or incomplete.

## Documentation is not `READY`

A page in `/docs` may describe a valid result, an invalid attempt, a blocked path, or incomplete work. `READY` is a separate status that requires the applicable checks and acceptance criteria to pass. A tip-cite, confident summary, or untested or blocked work is never `READY`. Do not invent scores or mark open, blocked, incomplete, or unresolved work `READY`.

## Tip-cite bank


When recording a merged documentation or stewardship change, use:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

Use the first eight hexadecimal characters of the merge commit on `main` and the actual pull-request number. Resolve both only after the pull request exists and is merged. Never use a branch tip, invent or pad a tip, invent a PR number, or reuse an older cite. A tip-cite records provenance only; it never establishes `READY`.

See [Contributing](../CONTRIBUTING.md#tip-cite-bank) and the [open problems tip-cite protocol](OPEN_PROBLEMS.md#tip-cite-protocol) for the shared steward procedure.

## Honesty footer

This index reports documentation scope and evidence boundaries; it does not establish completion, production readiness, a universal winner, or a score. Open problems and unknowns remain open until the applicable checks, approvals, and retained evidence exist.
