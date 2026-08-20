# Highlander

## There can be only one.

Highlander is a reproducible local acceptance lab for measuring how AI coding harnesses affect the work produced by the same underlying model. It evaluates correct, maintainable changes that survive deterministic checks while retaining the control, operator-attention, recovery, and cleanup evidence needed to trust the result.

This is a harness experiment, not a model leaderboard. In the primary lane, every contender receives the same task, repository snapshot, exact model, acceptance tests, and safety boundaries. The harness is the experimental variable; its tools, memory, permissions, orchestration, prompt handling, and recovery behavior are recorded alongside the resulting artifacts.

## Evidence at a glance

Start with the retained [T002 quota-free protocol bundle](results/fake-t002-protocol-r1/README.md). It ties 48 sanitized artifacts to MatchRunner commit `383b7a7`, proves the all-ready release and parent-owned qualification path with two deterministic fake Contenders, and records zero model calls and zero cost. Its claim boundary is intentionally narrow: it validates the evidence protocol, not real-harness coding performance.

Verify the complete bundle locally:

```text
python3 tools/evidence-bundle.py verify results/fake-t002-protocol-r1
```

The next evidence gate is a repeated, evaluator-backed result from real clean-room Harness Adapters. Until that exists, Highlander does not claim a real-harness winner.

Current control and challengers:

| Lane | Stack | Experimental question |
|---|---|---|
| Control | Ghostty → Herdr → OMP | What does the current harness produce with the fixed model? |
| Control-plus | Ghostty → Herdr → OMP → optional CCGram | Does phone supervision improve continuity without changing the coding runtime? |
| Challenger | OpenCode | Does a different coding runtime improve tool use, permissions, or recovery for that same model? |
| Challenger | Ghostty → Herdr → Pi + Firstmate | Does a Pi-based factory layer improve planning, crew coordination, and delivery with the same model? |
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
- Desktop applications are excluded from the primary lane. A stack must prove CLI, macOS/Linux/WSL, Herdr, legitimate subscription routes, and phone observe/respond capability before it can displace the control.

## Quick start

Inspect the deterministic fake Match without changing anything:

```text
python3 tools/highlander.py doctor examples/matches/fake-t001.json
python3 tools/highlander.py run examples/matches/fake-t001.json
```

Inspect the exact zero-cost T002 protocol Match retained above:

```text
python3 tools/highlander.py doctor examples/matches/fake-t002-protocol-r1.json
python3 tools/highlander.py run examples/matches/fake-t002-protocol-r1.json
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

Real Harness Adapters are deliberately blocked from host execution. Highlander never changes the normal Harness installation, authentication, Herdr integrations, or model selection.

Digest-pinned OMP, OpenCode, Codex, Hermes, and NanoBot execution is available only through the disposable OCI clean room. It creates independent clones with no publication remote, starts each Harness without host configuration, evaluates the raw result, captures tracked and untracked changes, and destroys Trial state. See [docs/CLEAN-ROOM.md](docs/CLEAN-ROOM.md) for image build, clean login seeds, Match generation, and execution. Host execution remains blocked.

The original `tools/prepare-run.sh` remains available as a legacy worktree-only preparer while MatchRunner matures.

Score a completed legacy pilot run after collecting the evidence bundle:

```text
python3 tools/score-run.py --scorecard path/to/scorecard.json
```

The first HarnessBench-aligned coding/DevOps season is frozen in
`benchmark-packs/hb-devhard-v1.json`. Its outcome leaderboard is intentionally
separate from the legacy weighted scorecard:

```text
python3 tools/hb-leaderboard.py \
  --manifest benchmark-packs/hb-devhard-v1.json \
  --results results/hb-devhard-v1/results.jsonl
```

See [docs/LEADERBOARD.md](docs/LEADERBOARD.md) for the best-attempt,
reliability, invalid-run, and ranking contract.

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
- `docs/MOBILE-SUPERVISION.md` — phone monitoring/responding protocol and control-plane ablations.
- `docs/MATCH-RUNNER.md` — pilot CLI, state machine, adapter boundary, and tmux workflow.
- `docs/CLEAN-ROOM.md` — pinned images, authentication seeds, disposable clones, raw evaluation, and cleanup.
- `docs/LEADERBOARD.md` — the HarnessBench developer-season ranking and result-ledger contract.
- `docs/EVIDENCE.md` — public Evidence Bundle, control proof, redaction, and qualification contract.
- `benchmark-packs/` — frozen upstream task packs, controls, versions, hashes, and declared deviations.
- `tasks/` — public task cards and task authoring rules.
- `fixtures/` — small executable targets for calibration; never treat them as production-quality applications.
- `tools/prepare-run.sh` — reproducible worktree and task-packet preparation.
- `tools/highlander.py` — source-checkout CLI for planning and running Matches.
- `tools/score-run.py` — dependency-free weighted scoring and disqualification.
- `tools/hb-leaderboard.py` — deterministic capability and reliability views for HarnessBench-aligned seasons.
- `tools/evidence-bundle.py` — fail-closed public export and manifest verification for retained Match evidence.
- `schemas/` — machine-readable run and scorecard contracts.
- `results/` — the public result-artifact contract; add actual runs only after redaction and review.
- `tests/` — tests for the benchmark kit itself.

## Result attribution

Every published result must make the causal comparison inspectable. At minimum, show the fixed model identity and limits, harness name and version, enabled tools and MCP servers, memory mode and seed state, permission policy, subagent settings, prompt packet, transcript, tool ledger, diff, tests, review, CI, and operator interventions. A result without this metadata is a score, not an explanation of how the harness affected the model.

## Future hiring use

If Highlander becomes a hiring artifact, add sanitized task packs and public evaluator instructions only after removing private provider details, proprietary code, hidden gold patches, and personal workflow configuration. Hiring scores should be one signal among engineering judgment, communication, security thinking, and code review—not an autonomous-agent leaderboard.
