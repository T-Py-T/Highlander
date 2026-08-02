# Highlander

## There can be only one.

Highlander is a private, reproducible gauntlet for comparing AI coding harnesses on the work that matters: correct, maintainable changes that survive tests, review, CI, and human scrutiny.

This is an experiment harness, not a popularity contest. Agents receive the same task, repository snapshot, model lane, acceptance tests, and safety boundaries. Their traces and artifacts are scored after the match.

Current control and challengers:

| Lane | Stack | Question |
|---|---|---|
| Control | Ghostty → Herdr → OMP | What does the current workflow really produce? |
| Challenger | OpenCode | Does a different coding runtime improve tool use, permissions, or recovery? |
| Challenger | Hermes Agent | Does persistence and remote autonomy reduce supervision for operational work? |
| Conditional | Goose → ACP → native Claude/Codex/Pi | Can subscription reuse add leverage without unsafe credential brokering? |

## Design principles

- Same task, same base SHA, same exact model when the lane permits it.
- Separate harness-controlled results from subscription-realism results.
- Score retained evidence, not agent self-report.
- A false green is worse than a slow failure.
- No merge, deploy, production credentials, or branch-rule changes.
- Run DevOps and SCADA/MES matches only in disposable, simulated, or read-only environments.
- Keep the benchmark private while the rubric and task quality mature.

## Quick start

Prepare isolated worktrees for a match:

```text
./tools/prepare-run.sh \
  --repo "$PWD" \
  --task-file tasks/T001-race-fix.md \
  --base-ref master \
  --model-id provider/exact-model-id \
  --provider provider-name \
  --stacks omp,opencode,hermes
```

The preparer records one base SHA and creates one detached worktree per contender. It does not install software, authenticate, launch agents, push, merge, or deploy.

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
7. Publish only a private comparison report until the task and rubric are trusted.

## Repository map

- `docs/GAUNTLET.md` — rules, scoring, evidence, and hiring-readiness guidance.
- `tasks/` — public task cards and task authoring rules.
- `fixtures/` — small executable targets for calibration; never treat them as production-quality applications.
- `tools/prepare-run.sh` — reproducible worktree and task-packet preparation.
- `tools/score-run.py` — dependency-free weighted scoring and disqualification.
- `schemas/` — machine-readable run and scorecard contracts.
- `tests/` — tests for the benchmark kit itself.

## Future hiring use

If Highlander becomes a hiring artifact, add sanitized task packs and public evaluator instructions only after removing private provider details, proprietary code, hidden gold patches, and personal workflow configuration. Hiring scores should be one signal among engineering judgment, communication, security thinking, and code review—not an autonomous-agent leaderboard.
