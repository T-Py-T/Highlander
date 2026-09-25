# Roadmap

This roadmap records candidate work for future Highlander seasons and stewardship. It is a planning document, not an acceptance gate, scorecard, release declaration, or claim that any item is complete or `READY`.

## Candidate work

- **Keep evidence reproducible.** Preserve frozen protocols, task bytes, controls, evaluator inputs, manifests, and public evidence bundles so each published result remains inspectable.
- **Improve invalid and incomplete-run handling.** Keep blocked, unavailable, invalid, and unscored slots visible; document replacement and publication rules before changing a season.
- **Expand coverage deliberately.** Add model strata, task packs, execution lanes, or supervision experiments only with a declared protocol and separate evidence. Do not pool unlike lanes or turn a version-bound observation into a universal winner claim.
- **Strengthen operational boundaries.** Continue reviewing clean-room isolation, provider authorization, spend limits, redaction, cleanup, and retention without retaining credentials or unnecessary private data.
- **Make stewardship decisions explicit.** Revisit open questions in the [open problems inventory](docs/OPEN_PROBLEMS.md) before treating a proposed capability or result as established.

These are candidates, not promises or completion claims. Priority, scope, and acceptance criteria remain subject to maintainer review and inspectable evidence.

## Honesty and score discipline

A roadmap entry does not prove implementation, qualification, release, production readiness, or a successful season. Work that is open, blocked, incomplete, untested, invalid, unavailable, or unresolved must not be marked `READY`. A summary, configured value, partial trace, or favorable result cannot establish a status by itself.

Missing, unavailable, invalid, or unscored results stay visible as such. Never infer a score, rank, completion, model identity, cost, or process outcome from silence, and never pad a score to fill a missing slot. Results remain bound to the named harness versions, model route, task pack, evaluator, controls, permissions, and run period; unlike lanes must not be pooled without a documented protocol that establishes comparability.

## Tip-cite protocol

For a merged result, record the repository, the actual pull request, and the exact eight-character hexadecimal tip from the merge commit on `main`:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

The cited tip is exactly the first eight characters of the merge commit's hexadecimal object ID (`[0-9a-f]{8}`), and `PR#<number>` is the actual pull-request number. Resolve both only after the pull request exists and is merged. Never use a branch tip, invent or pad a tip, invent a PR number, or reuse an older cite. A tip-cite records provenance only; it never establishes `READY`.

## Honesty footer

This roadmap reports candidate direction and evidence boundaries; it does not establish completion, production readiness, a universal winner, or a score. Open problems and unknowns remain open until the applicable checks, approvals, and retained evidence exist.
