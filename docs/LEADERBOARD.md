# Highlander developer-season leaderboard

The leaderboard answers one narrow question: with the model, reasoning level,
task bytes, evaluator, limits, and clean configuration held fixed, which
Harness produces the strongest coding and DevOps results?

## Hard-first six-Harness season

`benchmark-packs/hb-devhard-hardcore-v1-r3.json` freezes nine unchanged official
HarnessBench coding and DevOps tasks. The field is OMP (the current control),
OpenCode, Codex, Hermes, Atomic, and NanoBot. Each Harness receives three fixed
attempt slots per task, for 27 scored slots per Harness and 162 total slots.

The tasks run in two declared stages. The first stage starts with the five
hardest architecture, schema migration, database safety, service dependency,
and SQL rollback tasks. The second stage adds monorepo repair, flaky-test root
cause, Compose repair, and CLI parser testing. The task bytes and upstream
evaluators are unchanged.

This is the stack-displacement season. Its headline `Overall` score is the
mean of the nine per-task means across all valid attempts. That measures
typical performance across the workload rather than selecting each Harness's
best try. The per-task matrix is mandatory, so the aggregate can always be
traced back to the tasks a Harness solved or missed.

The season remains provisional until every clean-core route qualifies under
the corrected r3 protocol. An unavailable lane is shown as unavailable, never
as zero. The six r1 route calls are retained as invalid infrastructure evidence:
the protocol freezer omitted `expected_runtime_reasoning`, so the controller
rejected every response before scoring. R2 then qualified OMP, Hermes, Atomic,
and NanoBot but retained OpenCode and Codex as unavailable because Podman
populated their home directories as root-owned. R3 moves all home/XDG state
under a fresh writable tmpfs child without changing the benchmark matrix.

The executable protocol is
`protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r3.json`, SHA-256
`3c116fcecca9e63076df671b78be14703556b4bc66d11513001b11dd247df76b`.
It adds six unscored route-qualification calls before the 162 scored slots and
uses the unchanged upstream renderer and deterministic oracles. Reproduction
and redacted-export commands are in [SEASON-RUNBOOK.md](SEASON-RUNBOOK.md).

## Original breadth season

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

The hard-first season's primary rank is the mean of each task's mean valid
outcome across the three attempts. This is the expected or typical outcome.
The original breadth season retains its frozen primary: the mean of each
task's best valid outcome. That older primary measures demonstrated maximum
capability, not what the user should expect every day.

The same leaderboard must also show:

- mean and median across all valid attempts;
- mean of each task's worst valid attempt;
- full-credit and zero-score rates;
- attempt-score dispersion and mean within-task range;
- invalid attempts, elapsed time, and operator interventions; and
- every per-task mean and worst–best attempt range.

Best-of-three is never the hard-first headline and is never published by
itself. Process judging, when authorized,
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

Build the empty, provisional hard-first matrix before running any paid Trial:

```text
python3 tools/hb-leaderboard.py \
  --manifest benchmark-packs/hb-devhard-hardcore-v1-r3.json \
  --results /dev/null \
  --format markdown
```

Append one retained row for each fixed attempt slot as Trials complete. A
complete hard-first leaderboard contains a row for every Harness/task/attempt
combination and shows a separate score cell for all nine tasks.

## Interpretation gate

Do not spend research or model budget inventing harder tasks until the complete
nine-task matrix exists. Trigger a deep-research successor only if at least
three current Harnesses exceed 0.90 overall and at least 70% of current-Harness
task means exceed 0.95. That is evidence that the official pack is saturating,
not merely that one task was easy. The successor should emphasize
repository-scale bug repair, Terraform/Kubernetes/CI, migration recovery,
deployment rollback, and offline incident diagnosis.

## Retained task-043 pilot

`hb-devhard-043-gpt54-medium-host4-r1` is the first real, repeated
HarnessBench-aligned pilot. It used **only** official task
`043-db-migration-safety`,
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

The next highest-evidence run is the hard-first six-Harness season above. It
remains a separate clean-core stratum and must not be blended with this
host-isolated one-task pilot.
