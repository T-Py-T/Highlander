# Highlander developer-season leaderboard

The leaderboard answers one narrow question: with the model, reasoning level,
task bytes, evaluator, limits, and clean configuration held fixed, which
Harness produces the strongest coding and DevOps results?

## First season

`benchmark-packs/hb-devhard-v1.json` freezes 12 unmodified tasks from one
Qihoo360 HarnessBench commit. It includes four current Harnesses and NanoBot as
a historical temporal proxy. Public HarnessBench scores remain context; they
are not the acceptance tolerance for the local season.

The pack deliberately excludes `088-api-contract-mock-client-compat`. Its
runtime hook requires a public tunnel, which would mix external network
reachability into the coding comparison. Official offline task
`082-compose-config-repair` replaces it before any run or score.

## Attempts and invalid runs

Each Harness receives three scored slots for every task. A valid result owns
its slot permanently, including a zero. Never rerun a poor valid result.

Infrastructure-invalid runs remain in the append-only JSONL ledger and may be
replaced in the same slot. A contender is rankable only after every expected
slot has exactly one valid result. This keeps flaky infrastructure visible
without rewarding result shopping.

## Views

The primary rank is the mean of each task's best valid outcome across the
three attempts. It measures demonstrated maximum capability, not what the user
should expect every day.

The same leaderboard must also show:

- mean and median across all valid attempts;
- mean of each task's worst valid attempt;
- full-credit and zero-score rates;
- attempt-score dispersion and mean within-task range;
- invalid attempts, elapsed time, and operator interventions; and
- every per-task score.

Best-of-three is never published by itself. Process judging, when authorized,
is a separate frozen-judge lane and is never fabricated from outcome scores.
The legacy Highlander weighted scorecard does not apply to this season.

## Build a leaderboard

Store one JSON object per execution in an append-only file. `attempt` is the
fixed scored slot; `run_id` identifies the actual execution, including invalid
replacements.

```json
{"run_id":"omp-039-a1-r1","season_id":"hb-devhard-v1-gpt-5.4-medium-r1","task_id":"039-repo-architecture-map","harness_id":"omp","attempt":1,"qualification":"valid","outcome_score":0.84,"elapsed_seconds":312.4,"intervention_count":0}
```

```text
python3 tools/hb-leaderboard.py \
  --manifest benchmark-packs/hb-devhard-v1.json \
  --results results/hb-devhard-v1/results.jsonl \
  --format markdown
```

The JSON form is the stable input for a future private web leaderboard:

```text
python3 tools/hb-leaderboard.py \
  --manifest benchmark-packs/hb-devhard-v1.json \
  --results results/hb-devhard-v1/results.jsonl \
  --format json
```

## Interpretation gate

Do not build custom harder tasks until at least two modern Harnesses exceed
0.90 primary best outcome and 0.85 mean outcome with low dispersion. If that
trigger fires, the next pack should emphasize repository-scale repair,
Terraform/Kubernetes/CI, migration safety, rollback, and offline incident
diagnosis.

## Retained task-043 pilot

`hb-devhard-043-gpt54-medium-host4-r1` is the first real, repeated
HarnessBench-aligned pilot. It used official task `043-db-migration-safety`,
GPT-5.4 at medium reasoning, three attempts per available Harness, and the
deterministic upstream oracle. It is a **host-isolated subscription-realism**
stratum because the canonical disposable login seeds were unavailable. It is
not the clean-core season and is not rankable as a season.

| Harness | Per-trial outcome | Mean | Population σ | Mean seconds |
|---|---|---:|---:|---:|
| OpenCode 1.18.15 | 0.995, 0.995, 0.987 | 0.9923 | 0.0038 | 209.134 |
| Hermes 0.20.0 | 0.995, 0.995, 0.980 | 0.9900 | 0.0071 | 275.101 |
| OMP 17.2.10 | 0.909, 0.909, 0.995 | 0.9377 | 0.0405 | 319.955 |
| Codex 0.149.0 | 0.917, 0.270, 0.987 | 0.7247 | 0.3228 | 278.197 |
| NanoBot | unavailable | — | — | — |

All 12 scheduled paid Trials were valid and required zero operator
interventions. Codex's 0.270 Trial is a valid failure, not infrastructure
noise: independent rescoring reproduced a foreign-key constraint failure.
NanoBot had no qualified dedicated host OAuth profile and was not scored zero.

No process judge ran, so process and combined scores are null. Native event,
tool-invocation, duration, and usage records are observations only; their
accounting semantics differ among Harnesses. This one-task pilot estimates
within-task repeatability and must not declare a winner.

Verify the 314-file sanitized evidence bundle:

```text
python3 tools/hb-evidence.py verify \
  results/hb-devhard-043-gpt54-medium-host4-r1
```

The next highest-evidence run is the same frozen control across the remaining
11 DevHard tasks. The full-pack season should remain a separate stratum unless
the five disposable subscription seeds are requalified first.
