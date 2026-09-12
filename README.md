# Highlander

Highlander is a local gauntlet for comparing AI coding-agent harnesses under controlled models, tasks, and evaluators. It schedules repeatable matches, runs contenders in disposable environments, evaluates their changes, and retains the evidence needed to inspect each result.

Use Highlander when you need to compare the effect of harness tools, memory, permissions, orchestration, or recovery behavior without treating a model change as a harness result.

## Current result

The primary public baseline used GPT-5.4 with medium reasoning, nine unchanged HarnessBench coding and DevOps tasks, and three attempts per harness.

![GPT-5.4 hard coding and DevOps harness results](docs/assets/gpt54-hard-season-results.svg)

| Rank | Harness | Overall outcome | Attempt σ | Valid slots |
|---:|---|---:|---:|---:|
| 1 | Codex CLI 0.147.0 | 0.9299 | 0.0880 | 27/27 |
| 2 | OpenCode 1.18.15 | 0.9244 | 0.0896 | 27/27 |
| 3 | OMP 17.2.10 | 0.8968 | 0.1528 | 27/27 |
| 4 | Hermes 0.20.0 | 0.7533 | 0.2943 | 27/27 |
| 5 | NanoBot 0.1.5.post3 | 0.1801 | 0.0775 | 27/27 |
| — | Atomic 0.9.15 | 0.9158 valid-only | 0.0985 | 26/27; unranked |

Five harnesses completed all 27 slots. Atomic retained one timeout and remains unranked. Codex CLI's 0.0055 lead over OpenCode is smaller than either harness's run-to-run dispersion, so this result is a version-bound observation rather than a universal winner claim.

See the [full leaderboard](results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1/leaderboard.md) for per-task means, attempt ranges, validity, and the retained evidence bundle.

## Inspect a match safely

Check the included fake match and print its execution plan:

```sh
python3 tools/highlander.py doctor examples/matches/fake-t001.json
python3 tools/highlander.py run examples/matches/fake-t001.json
```

`run` is a dry run unless you pass `--execute`. The plan records the base commit, task hash, worktree and evidence paths, adapter versions, model controls, and redacted invocations. These commands do not create worktrees, start harnesses, or make model calls.

Run the complete local repository gate:

```sh
pre-commit run --all-files --verbose
```

The test suite and retained fixtures use synthetic data. Real harness execution is restricted to the disposable clean-room path and requires separate credentials and cost approval.

## How a match works

1. A match fixes the repository commit, task, evaluator, model controls, limits, and permissions.
2. Highlander prepares an isolated trial for each contender.
3. Each harness receives the same visible task packet.
4. Deterministic evaluators score the resulting repository state.
5. Highlander retains the transcript, tool ledger, diff, tests, evaluator output, usage observations, and operator interactions.
6. The leaderboard ranks only valid, comparable trials and keeps invalid attempts visible.

## Documentation

- [Gauntlet design](docs/GAUNTLET.md) defines the comparison rules and scoring model.
- [Match runner](docs/MATCH-RUNNER.md) describes the CLI, state machine, adapters, and tmux workflow.
- [Clean-room execution](docs/CLEAN-ROOM.md) covers disposable images, isolated homes, authentication seeds, and cleanup.
- [Leaderboard contract](docs/LEADERBOARD.md) defines ranking, reliability, and invalid-run handling.
- [Season runbook](docs/SEASON-RUNBOOK.md) gives the qualification, execution, export, and verification steps.
- [Evidence contract](docs/EVIDENCE.md) defines public bundles, redaction, and manifest verification.
- [Mobile supervision](docs/MOBILE-SUPERVISION.md) describes observe-and-respond experiments.
- [Security policy](SECURITY.md) explains how to report vulnerabilities and what must stay out of retained evidence.

## Limits

- Results apply to the named harness versions, model route, task pack, controls, and run period.
- Native token and cost fields are not comparable across all harnesses because providers expose different accounting data.
- HarnessBench inputs, provider software, and captured third-party output keep their original licenses and terms.
- Personal plugins, extensions, rules, memory, MCP servers, and operator steering are excluded from the primary controlled lane.
- Desktop applications are outside the primary lane.

## License

Original Highlander code, tests, schemas, and documentation are available under the [MIT License](LICENSE). Third-party inputs and captured outputs remain under their original terms. See [third-party notices](THIRD_PARTY_NOTICES.md).
