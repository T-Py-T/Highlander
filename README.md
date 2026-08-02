# Highlander

## There can be only one.

Highlander is a private, reproducible gauntlet for measuring how AI coding harnesses affect the work produced by the same underlying model. It evaluates correct, maintainable changes that survive tests, review, CI, and human scrutiny.

This is a harness experiment, not a model leaderboard. In the primary lane, every contender receives the same task, repository snapshot, exact model, acceptance tests, and safety boundaries. The harness is the experimental variable; its tools, memory, permissions, orchestration, prompt handling, and recovery behavior are recorded alongside the resulting artifacts.

Current control and challengers:

| Lane | Stack | Experimental question |
|---|---|---|
| Control | Ghostty → Herdr → OMP | What does the current harness produce with the fixed model? |
| Challenger | OpenCode | Does a different coding runtime improve tool use, permissions, or recovery for that same model? |
| Challenger | Hermes Agent | Does persistence and remote autonomy reduce supervision for that same model? |
| Conditional | Goose → ACP → native Claude/Codex/Pi | Does subscription reuse add harness leverage without changing the model comparison? |

## Design principles

- Same task, same base SHA, same exact model, and comparable limits in the primary harness-controlled lane.
- Never interpret a model change as a harness win. If a contender cannot run the fixed model, record it as a separate subscription-realism result.
- Separate harness-controlled results from subscription-realism results.
- Score retained evidence, not agent self-report.
- Publish the model and harness metadata together so readers can attribute output differences to the available environment.
- A false green is worse than a slow failure.
- No merge, deploy, production credentials, or branch-rule changes.
- Run DevOps and SCADA/MES matches only in disposable, simulated, or read-only environments.
- Keep the benchmark private while the rubric and task quality mature.

## Quick start

Inspect the deterministic fake Match without changing anything:

```text
python3 tools/highlander.py doctor examples/matches/fake-t001.json
python3 tools/highlander.py run examples/matches/fake-t001.json
```

`run` is a dry-run unless `--execute` is present. The plan records one base SHA, the exact Task hash, worktree and evidence paths, adapter versions, model controls, and redacted invocations. It does not create worktrees or panes and cannot make a model call.

Execute two quota-free fake Contenders headlessly or in one detached tmux window:

```text
python3 tools/highlander.py run examples/matches/fake-t001.json \
  --save-plan /tmp/highlander-fake-plan.json
python3 tools/highlander.py run examples/matches/fake-t001.json \
  --plan /tmp/highlander-fake-plan.json --execute
python3 tools/highlander.py run examples/matches/fake-t001.json \
  --session tmux --save-plan /tmp/highlander-fake-tmux-plan.json
python3 tools/highlander.py run examples/matches/fake-t001.json \
  --session tmux --plan /tmp/highlander-fake-tmux-plan.json --execute
```

Change `match_id` before repeating an executed Match. Match directories and worktrees are retained intentionally for audit. The pilot does not delete them automatically.

Inspect the planned OMP-versus-OpenCode low-reasoning command crosswalk:

```text
python3 tools/highlander.py doctor \
  examples/matches/omp-opencode-low-reasoning.json
python3 tools/highlander.py run \
  examples/matches/omp-opencode-low-reasoning.json
```

Real Harness Adapters are deliberately execution-blocked until native event capture and configured/runtime/provider control proof are implemented. Highlander never installs a harness, authenticates, copies credentials, updates Herdr integrations, or silently substitutes a model.

The original `tools/prepare-run.sh` remains available as a legacy worktree-only preparer while MatchRunner matures.

Score a completed run after collecting the evidence bundle:

```text
python3 tools/score-run.py --scorecard path/to/scorecard.json
```

Run the local checks:

```text
python3 -m unittest discover -s tests
```

## Match lifecycle

1. Calibrate the visible task and evaluator-only checks.
2. Freeze the target repository at an exact commit.
3. Prepare one isolated worktree per contender.
4. Paste the same task packet into each harness.
5. Preserve transcripts, tool events, diffs, tests, review, CI, cleanup, and operator interactions.
6. Score hard gates first, then the weighted result.
7. Store one result directory per harness, then publish only a redacted comparison report when the task and rubric are trusted.

## Repository map

- `docs/GAUNTLET.md` — rules, scoring, evidence, and hiring-readiness guidance.
- `docs/MATCH-RUNNER.md` — pilot CLI, state machine, adapter boundary, and tmux workflow.
- `docs/EVIDENCE.md` — public Evidence Bundle, control proof, redaction, and qualification contract.
- `tasks/` — public task cards and task authoring rules.
- `fixtures/` — small executable targets for calibration; never treat them as production-quality applications.
- `tools/prepare-run.sh` — reproducible worktree and task-packet preparation.
- `tools/highlander.py` — source-checkout CLI for planning and running Matches.
- `tools/score-run.py` — dependency-free weighted scoring and disqualification.
- `schemas/` — machine-readable run and scorecard contracts.
- `results/` — the public result-artifact contract; add actual runs only after redaction and review.
- `tests/` — tests for the benchmark kit itself.

## Result attribution

Every published result must make the causal comparison inspectable. At minimum, show the fixed model identity and limits, harness name and version, enabled tools and MCP servers, memory mode and seed state, permission policy, subagent settings, prompt packet, transcript, tool ledger, diff, tests, review, CI, and operator interventions. A result without this metadata is a score, not an explanation of how the harness affected the model.

## Future hiring use

If Highlander becomes a hiring artifact, add sanitized task packs and public evaluator instructions only after removing private provider details, proprietary code, hidden gold patches, and personal workflow configuration. Hiring scores should be one signal among engineering judgment, communication, security thinking, and code review—not an autonomous-agent leaderboard.
