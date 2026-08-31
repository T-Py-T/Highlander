# Public result contract

Highlander results are evidence packages, not just leaderboard numbers. The purpose of publishing them is to show how the same model behaved when the harness changed.

## Experimental rule

For a primary comparison, every result in a match must use the same exact model, provider route, model parameters, context/turn limits, task version, repository base SHA, and acceptance tests. The harness may change. Record the harness's tools, MCP servers, memory, permissions, subagents, prompt handling, and recovery behavior.

If a harness cannot use the fixed model because of subscription or provider restrictions, keep it in a separate subscription-realism match. Never combine those results with the same-model ranking.

## Directory layout

Create one immutable directory per Match and one Trial directory per Contender and attempt:

```text
results/
  MATCH-ID/
    match-spec.json
    execution-plan.json
    control-profile.json
    match-result.json
    artifact-manifest.json
    task/
    journal/
    session/
    trials/
      omp/attempt-001/
      opencode/attempt-001/
    evaluation/
    report/
```

`execution-plan.json` freezes the task hash, base SHA, exact model route, controls, adapters, worktrees, and lane. Each `capability.json` records what that harness exposed before release. Native and ATIF evidence record what it actually used, including failed or denied calls. See `docs/EVIDENCE.md` for the complete contract.

## Redaction before publication

- Remove credentials, tokens, private repository URLs, personal paths, subscription identifiers, and proprietary source.
- Replace secrets with stable placeholders so the transcript remains understandable.
- Keep hidden evaluator tests and gold patches private until the benchmark is intentionally released.
- Do not publish a score without its supporting transcript, tool ledger, diff, tests, review, CI, and operator log.
- Mark missing or redacted evidence explicitly; never imply that an unrecorded capability was absent or unused.

## Comparison report

`comparison.md` should include a compact table with the fixed model and a row per harness, followed by:

- capability differences before the run;
- actual tool and memory usage;
- operator interventions and recovery events;
- correctness and maintainability findings;
- hard gates and invalidating factors;
- weighted score and correct maintainable draft PRs per active operator hour;
- limitations, repeat count, and whether the result is stable enough to influence the stack.

The first real-harness result is
`hb-devhard-043-gpt54-medium-host4-r1/`. It is a repeated, identical-model
host-isolated subscription-realism pilot, not a clean-room season or a winner
claim. Its private byte-retained source remains outside Git; the checked-in
copy retains path-redacted native transcripts, tool ledgers, diffs, final
workspaces, deterministic oracle output, usage observations, cleanup proof,
and self-verifying manifests.

Verify it with:

```text
python3 tools/hb-evidence.py verify \
  results/hb-devhard-043-gpt54-medium-host4-r1
```

The bundle's `results.jsonl`, `leaderboard.json`, `summary.json`, and
`report.md` are canonical views of the same 12 valid Trials. Process and
combined scores are null because no process judge ran. NanoBot is explicitly
unavailable, not scored zero.

## Retained hard coding and DevOps seasons

The primary same-model baseline is
`hb-devhard-hardcore-v1-gpt-5.4-medium-r1/`: nine unchanged HarnessBench tasks,
six harnesses, and three attempts per harness/task. Five harnesses have 27/27
current valid slots. Atomic has 26/27 and is shown without a rank. Its public
bundle contains 6,090 manifest-verified artifacts and retains every original
and replacement result row.

The successor model stratum is
`hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4/`. It uses the same task matrix
but is not pooled with GPT-5.4. Both seasons keep process and combined scores
null because no process judge ran, and both expose native usage with explicit
coverage rather than inventing missing tokens or subscription costs.

Verify both immutable bundles:

```text
python3 tools/hb-evidence.py verify-season \
  results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1
python3 tools/hb-evidence.py verify-season \
  results/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4
```

## Retained protocol qualification

`fake-t002-protocol-r1/` is the first retained public bundle. It contains 48 manifest-verified artifacts from two deterministic fake Contenders and is tied to the exact clean MatchRunner and Arena commit. It is deliberately labeled as protocol evidence rather than a real-harness comparison: no model was called, T002 was not solved, and no performance rank can be inferred.

Verify its integrity from the repository root:

```text
python3 tools/evidence-bundle.py verify results/fake-t002-protocol-r1
```

Public export verifies the sealed source manifest, copies only manifested artifacts, excludes raw worktrees/workspaces, replaces machine-local roots, scans for high-confidence credential material, records clean runner provenance, and generates a fresh public manifest. Export fails if the source is tampered with or the runner worktree is not tied to one clean commit.
