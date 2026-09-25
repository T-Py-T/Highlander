# Open problems inventory

This page records questions Highlander has not closed. It is an inventory for
stewardship and future seasons, not an acceptance gate, scorecard, or claim that
any item is solved. An open, blocked, or untested item is not `READY`.

See [Contributing](../CONTRIBUTING.md) for contributor setup, evidence
boundaries, and tip-cite rules. Staffing-oriented project context is in
[What this proves](../README.md#what-this-proves).

## Claim scope and comparison

- **Version-bound results versus universal winner claims.** A result is bound to
  the named harness versions, model route, task pack, evaluator, controls,
  permissions, and run period. We still need a durable review habit and tooling
  that prevents a narrow season result from being repeated as a universal
  winner claim.
- **Season coverage.** Different model strata, task packs, clean-room modes,
  subscription-realism lanes, and historical proxies answer different
  questions. The evidence and leaderboards must remain separate until a future
  protocol proves that pooling is valid.
- **No invented scores.** Missing, unavailable, invalid, or unscored slots stay
  visible as such. No score, rank, completion, model identity, cost, or process
  outcome may be inferred from silence, a configured value, a partial trace, or
  a favorable summary.
- **No bake-off authority beyond documented seasons.** Highlander can describe
  and reproduce the seasons documented by their frozen protocols and retained
  evidence. It is not authority for an undocumented cross-season bake-off,
  vendor-wide ranking, or fresh winner claim merely because a comparison would
  be convenient.

## Execution and evidence boundaries

- **Live-execution cost and authorization.** The clean-room path separates
  dry-run planning from live execution, credentials, and cost approval. The
  remaining problem is making provider-specific spend, subscription limits,
  refresh behavior, rate limits, and cancellation boundaries consistently
  inspectable without retaining secrets or treating unlike accounting fields as
  comparable.
- **Authentication and account isolation.** Authentication seeds, provider
  grants, personal configuration, and operator access need continued review for
  least privilege, expiry, revocation, refresh races, and proof that one lane
  cannot contaminate another.
- **Evidence retention scope.** Retained evidence must be sufficient to inspect
  controls, actions, changes, evaluation, interventions, and cleanup, while
  excluding credentials, private prompts, hidden evaluators, proprietary
  source, and unnecessary personal data. The right retention horizon,
  redaction proof, and reproducibility level remain open for each lane.
- **Observability limits.** Native events, tool ledgers, transcripts, token
  counters, duration, and cost fields have different semantics across
  harnesses. Normalization must preserve unknowns and provenance rather than
  manufacture a common metric.
- **Operator and environment effects.** Memory, plugins, MCP servers, desktop
  state, warm caches, network reachability, intervention timing, and host
  contention can change a result. Their exclusion, isolation, or separate
  labeling needs to stay explicit for every season.

## Stewardship questions

- **Invalid and incomplete attempts.** The append-only ledger preserves them,
  but future season tooling should make replacement rules, rankability, and
  publication state equally clear to operators and readers.
- **Future authority.** A new task pack, model route, evaluator, or aggregation
  rule needs a frozen protocol, declared rationale, and separate evidence before
  it can support a new claim. Research pressure is not evidence of readiness.

## Status discipline

This inventory does not grant `READY`, qualify a trial, approve live execution,
rank a harness, or authorize a new season. Those statuses require the applicable
protocol, checks, approvals, and retained evidence. Do not fill unknowns with
invented scores or optimistic interpretations.

## Tip-cite protocol

For a merged result, cite the repository, pull request, and exact eight-character
hexadecimal tip from the merged commit on `main`:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

The Steward resolves the eight-character tip against `main`. Use the first eight
hexadecimal characters of the merge commit and the actual pull-request number
only after it exists; never invent a tip or reuse an older one. A tip-cite records
provenance and is never `READY` by itself.
