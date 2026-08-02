# MatchRunner pilot

MatchRunner is Highlander's local execution plane. It makes a controlled Match easy to repeat without making the terminal multiplexer responsible for scientific evidence.

## Interface

```text
highlander doctor MATCH.json
highlander run MATCH.json [--session headless|tmux] [--save-plan PLAN.json]
highlander run MATCH.json --plan PLAN.json --execute
highlander status RUN_DIRECTORY
highlander stop RUN_DIRECTORY
```

From a source checkout, substitute `python3 tools/highlander.py` for `highlander`.

- `doctor` probes binaries, versions, declared capabilities, model-control proof, and Session Adapter availability. It is read-only and never authenticates or changes configuration.
- `run` produces a complete dry-run plan by default. Save it outside the Arena, review it, then pass that exact file with `--plan --execute`. Execution recomputes every input and fails before side effects if the base ref, Task, adapter version, capability probe, session, or plan hash changed.
- `status` reads the append-only journal or completed Match result.
- `stop` currently terminates a retained tmux session. Foreground headless execution is owned by its controller.

## Execution flow

```text
Match JSON
   │
   ▼
MatchRunner ── freezes base SHA, Task hash, Control Profile, commands
   │
   ├── one detached Git worktree per Trial
   ├── one internal worker per Trial
   └── one Session Adapter for the whole Match
                 │
                 ├── headless processes
                 └── one tmux window, tiled panes
                              │
                    all workers announce ARMED
                              │
                    atomic start gate is released
                              │
                    native Harness Adapters submit
                    the exact stored Task bytes
```

The pilot's fake Harness Adapter makes no model calls. OMP and OpenCode produce redacted invocation plans but cannot execute yet. This is intentional: a Harness Adapter does not graduate until it can retain native events and verify configured, runtime, and provider/wire controls.

## Session boundary

The Session Adapter receives complete Highlander worker commands. It may create panes, capture presentation output, inspect process state, interrupt workers, and reconcile the session. It cannot:

- paste the Task into a harness;
- scrape a prompt marker to infer completion;
- interpret tool or model events;
- verify the effective model or reasoning level;
- declare a Trial qualified.

One Match uses one Session Adapter. Do not nest tmux inside Herdr. Herdr remains the preferred future operator-facing adapter; tmux is the implemented portable visible pilot across macOS, Linux, and WSL.

## Synchronization

Every pane starts `highlander _worker --trial-plan ...`. Workers write `worker-ready.json` and then wait for the same atomic `start-gate.json`. MatchRunner releases the gate only after every worker is ready. Each worker records the nanosecond at which it submits the Task, and the Match result reports observed start skew.

The concurrent lane measures realistic same-window contention and user experience. It does not replace randomized sequential matched blocks for primary efficacy claims.

## Lifecycle

```text
PLANNED → PREFLIGHTED → PREPARED → LAUNCHED → ARMED
        → RELEASED → COLLECTED → VERIFIED → COMPLETE
```

The journal is append-only JSONL. Terminal pane disappearance is never completion evidence. A worker outcome and required Evidence Bundle are needed before a Trial can qualify.

## Safety

- Dry-run is the default.
- Real adapter execution fails closed.
- Task bytes are hashed before execution and verified again by every worker.
- Commands are retained as argv arrays; credential values are never serialized.
- Fake workers receive an explicit environment allowlist and cannot inherit provider keys or OAuth variables. Future native adapters require a separate audited authentication policy before execution can be enabled.
- Adapter options use per-adapter allowlists; arbitrary headers, environment values, tokens, and unknown fields are rejected.
- Worktrees are detached from one frozen base SHA.
- Processes and sessions are reconciled automatically.
- Worktrees remain for inspection and are marked `retained_intentionally_for_review`; automatic deletion is outside the pilot.
- No merge, push, deployment, configuration update, or credential brokering exists in MatchRunner.

## Local validation

```text
python3 -m unittest discover -s tests -v
HIGHLANDER_TEST_TMUX=1 \
  python3 -m unittest \
  tests.test_match_runner.MatchRunnerTests.test_tmux_fake_match -v
```

The tmux test opens a detached local session containing only deterministic fake workers and closes it after evidence capture. It incurs no model cost.
