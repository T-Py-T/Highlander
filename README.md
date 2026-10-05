# Highlander

[![Highlander checks](https://github.com/T-Py-T/Highlander/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/T-Py-T/Highlander/actions/workflows/checks.yml)

**Same model, same task, same clock. The only thing that changes is the coding-agent harness.**

Give six agents one repository, one task, and one frozen model, and the diffs still diverge. Highlander is the gauntlet that keeps the model as a control and scores what the harness did with it: tools, memory, permissions, recovery, and the receipts. You can inspect a published season, or run a free fake match, without an account.

![GPT-5.4 hard coding and DevOps season, regenerated from the retained bundle](docs/assets/gpt54-hard-season-results.svg)

The figure above is the committed SVG for `hb-devhard-hardcore-v1-gpt-5.4-medium-r1`. A second existing chart, for the earlier single-task pilot, is [`docs/assets/harnessbench-task-043-results.svg`](docs/assets/harnessbench-task-043-results.svg). There is no hosted demo and no web leaderboard.

## Why try it

- **The model is not the score.** A primary match freezes provider, model id, reasoning level, context and turn limits, and forbids fallback. A harness that cannot hold that route is recorded as incompatible instead of quietly ranked.
- **A number you can rebuild.** Every published trial keeps the transcript, tool ledger, diff, tests, and a self-checking manifest. The leaderboard is a view over those rows, not a screenshot of a spreadsheet.
- **A free path before any paid call.** The fake match, `doctor`, the dry-run plan, and leaderboard regeneration use only this tree. Real harnesses are a different, heavier path, and this page does not pretend that path was run.

Vocabulary for match, trial, contender, control profile, arena, and evidence bundle is in [CONTEXT.md](CONTEXT.md).

## Worked example

Python 3.11 or newer. No install.

```sh
git clone https://github.com/T-Py-T/Highlander.git
cd Highlander
```

### 1. Preflight the fake match

`examples/matches/fake-t001.json` names two deterministic doubles, `fake-success` and `fake-harness-failure`. They are not coding agents.

```sh
python3 tools/highlander.py doctor examples/matches/fake-t001.json
```

`doctor` is read-only. On a clean checkout it reports `ready_for_execution: true` for this fixture and notes that no authentication, worktree, pane, or model call was changed.

### 2. Read the plan, then execute that exact plan

`run` without `--execute` prints the plan and stops. `--execute` by itself is rejected: the runner requires the plan you just reviewed.

```sh
python3 tools/highlander.py run examples/matches/fake-t001.json
python3 tools/highlander.py run examples/matches/fake-t001.json \
  --save-plan /tmp/fake-t001-plan.json
python3 tools/highlander.py run examples/matches/fake-t001.json \
  --execute --plan /tmp/fake-t001-plan.json
```

The dry run's safety block says `paid_model_calls_in_plan: false`. The executed fixture finishes `COMPLETE`: `fake-success` is `protocol_success`, `fake-harness-failure` is `protocol_harness_failure`, and both trials record `model_calls: 0` and `cost: 0`. That is the demo. It does not rank a product harness.

`examples/matches/omp-opencode-low-reasoning.json` is the same spec shape with two real harnesses and placeholder provider fields. Do not treat it as something this README ran.

### 3. Rebuild a published leaderboard

The checked-in season `results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1` is GPT-5.4 at medium reasoning, nine unmodified tasks from [Qihoo360/harness-bench](https://github.com/Qihoo360/harness-bench), six harnesses, three attempts each.

```sh
python3 tools/hb-evidence.py verify-season \
  results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1
```

A clean tree verifies 6,090 artifacts, `status: verified`, `season_status: provisional`, manifest `a77fb20926e1134fa3d54167bb8630c1516c2a6c2d4599e3ab6c8787f7b3c1eb`.

```sh
cd results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1
python3 ../../tools/hb-leaderboard.py \
  --manifest season-manifest.json \
  --results results.jsonl \
  --format markdown
```

Regenerating that markdown reproduces the committed [`leaderboard.md`](results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1/leaderboard.md). Names and versions below are the season manifest; scores are the regenerated ranking.

| Rank | Harness | Overall | Stddev | Valid slots |
|---:|---|---:|---:|---:|
| 1 | Codex CLI 0.147.0 | 0.9299 | 0.0880 | 27/27 |
| 2 | OpenCode 1.18.15 | 0.9244 | 0.0896 | 27/27 |
| 3 | Oh My Pi 17.2.10 | 0.8968 | 0.1528 | 27/27 |
| 4 | Hermes Agent 0.20.0 | 0.7533 | 0.2943 | 27/27 |
| 5 | NanoBot 0.1.5.post3 | 0.1801 | 0.0775 | 27/27 |
| — | Atomic 0.9.15 | 0.9158 valid-only | 0.0985 | 26/27, unranked |

Codex CLI's lead over OpenCode is smaller than either harness's dispersion. Read it as a version-bound observation, not a winner. Atomic kept one invalid slot, so it is shown and not ranked. Per-task ranges are in the regenerated markdown.

Each directory under `trials/` holds that attempt's diff, result, native transcript, tool ledger, and control proof. Disagree with a cell by reading the trial, not by arguing with the table.

## Honest demo

What the commands above establish, and what they do not:

- **No hosted demo, no external user.** Results are files in this repository. Nobody else's reproduction of a season is published here.
- **Both seasons are provisional.** `verify-season` and `leaderboard.md` label the GPT-5.4 bundle `provisional`. The season manifest's own status is `frozen_pending_runtime_qualification`. The companion season `results/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4` carries the same manifest status and is not pooled with GPT-5.4. This page does not restate its scores; re-run `verify-season` on that directory yourself. Process and combined scores stay null until a process judge exists.
- **The real-harness path was not run.** It needs a local OCI runtime, images from `python3 tools/clean-room.py`, your own provider credentials, and paid model calls. `--execute` on a real spec is that spend. [docs/CLEAN-ROOM.md](docs/CLEAN-ROOM.md) and [docs/SEASON-RUNBOOK.md](docs/SEASON-RUNBOOK.md) describe it. They are not a claim that it was exercised while writing this page.
- **Other bundles.** `results/hb-devhard-043-gpt54-medium-host4-r1` is the single-task pilot behind the second SVG. `results/fake-t002-protocol-r1` is a model-free protocol fixture. [`results/README.md`](results/README.md) says what each one does not establish.

A result names harness versions, model route, task pack, controls, and run period. It is not a claim about the next release. Missing token or cost fields stay missing. Desktop apps are out of scope.

## Getting started

The fake-match commands in the worked example are the start. Other subcommands: `status` reads a retained run directory, and `stop` ends an active tmux session.

To run the same local gate CI runs, from a virtualenv:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip pre-commit
pre-commit run --all-files --verbose
```

That gate runs unit tests, compile, `doctor` on the fake match, and evidence verification. It does not call a model.

## Contributing

Issues and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers the pre-commit gate and the rule that evidence is not a readiness claim: keep invalid and blocked outcomes visible. [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) applies to participants. Questions start at [SUPPORT.md](SUPPORT.md). Unresolved scope is listed in [docs/OPEN_PROBLEMS.md](docs/OPEN_PROBLEMS.md).

| Document | What it is |
|---|---|
| [Gauntlet design](docs/GAUNTLET.md) | Lanes, hard gates, scoring |
| [Match runner](docs/MATCH-RUNNER.md) | CLI, adapters, tmux |
| [Clean room](docs/CLEAN-ROOM.md) | Disposable images and credential seeds |
| [Leaderboard contract](docs/LEADERBOARD.md) | Ranking and invalid runs |
| [Evidence contract](docs/EVIDENCE.md) | Redaction and manifest checks |
| [Decision records](docs/adr/README.md) | Why the model is the control |
| [Security](SECURITY.md) | What must never enter retained evidence |

## License

Original Highlander code, tests, schemas, and documentation are [MIT](LICENSE). Third-party inputs and captured harness output stay under their own terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [NOTICE.md](NOTICE.md).
