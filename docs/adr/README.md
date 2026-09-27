# Architecture decision records

These records capture planning decisions, trade-offs, and architectural boundaries for Highlander. They document why a direction was chosen at a point in time; they are not acceptance gates, scorecards, release declarations, or claims that any decision is implemented, qualified, or `READY`.

Documentation here reports decision rationale and evidence boundaries. It does not establish production readiness, a universal winner, or completion when work is open, blocked, invalid, or incomplete.

## Index

| ADR | Title |
|---|---|
| [0001](0001-model-is-the-control.md) | Hold the model constant and evaluate the harness |
| [0002](0002-filesystem-backed-match-engine.md) | Use a filesystem-backed Match Engine with Harness and Session ports |

Individual ADR files are historical decision records. Do not rewrite their decision text to match later implementation; add a new ADR or update this index when stewardship needs a revised boundary.

## Decisions are not `READY`

An ADR records a decision or candidate direction, not inspectable proof that the decision was implemented, tested, or accepted. `READY` requires the applicable checks and acceptance criteria to pass. A tip-cite, confident summary, or untested or blocked work is never `READY`. Do not invent scores or mark open, blocked, incomplete, or unresolved work `READY`.

## Tip-cite protocol

For a merged documentation or stewardship change, record the repository, the actual pull request, and the exact eight-character hexadecimal tip from the merge commit on `main`:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

The cited tip is exactly the first eight characters of the merge commit's hexadecimal object ID (`[0-9a-f]{8}`), and `PR#<number>` is the actual pull-request number. Resolve both only after the pull request exists and is merged. Never use a branch tip, invent or pad a tip, invent a PR number, or reuse an older cite. A tip-cite records provenance only; it never establishes `READY`.

See [Contributing](../../CONTRIBUTING.md#tip-cite-bank) and the [open problems tip-cite protocol](../OPEN_PROBLEMS.md#tip-cite-protocol) for the shared steward procedure.

## Baseline provenance

Resolve ADR tip-cites against the current `main` tip. As of the stewardship baseline that includes roadmap tip-cite honesty (Ship173), `main` is:

```text
T-Py-T/Highlander 81e9cedf PR#62 — docs: add roadmap honesty and tip-cite protocol
```

Re-resolve this baseline after later merges; do not treat an older cite as current without checking `main`.

## Honesty footer

This index and the linked ADRs report planning decisions and evidence boundaries; they do not establish completion, production readiness, a universal winner, or a score. Open problems and unknowns remain open until the applicable checks, approvals, and retained evidence exist.
