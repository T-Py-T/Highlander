# Disposable clean-room workflow

The OCI Clean Room is Highlander's execution seam for raw Harness comparison. It starts every Contender from an immutable image, an independent clone, a fresh home directory, and an authentication-only seed. It retains the resulting patch and evidence, evaluates the patch unchanged, then destroys the container, evaluator copy, and Trial workspace.

There is deliberately no commit, push, PR, no-mistakes run, auto-fix, or post-Trial repair. Those activities would answer a shipping-workflow question rather than the raw Harness question.

## What is controlled

- The OMP, OpenCode, Codex, Hermes, NanoBot, and evaluator images are resolved to immutable local image IDs before planning.
- Every Trial clones the same base SHA with `--no-local`, checks out detached, and removes `origin` before the Harness starts.
- The same Task bytes, requested model, reasoning level, limits, and evaluator commands are frozen in the reviewed execution plan.
- The container root is read-only; Linux capabilities are dropped; `no-new-privileges`, CPU, memory, PID, and wall-time limits are applied.
- Only the independent workspace and an optional authentication seed are mounted. The host home, SSH keys, GitHub credentials, Docker socket, and normal Harness configuration are absent.
- OMP starts with extension, skill, rule, session, title, and prewalk discovery disabled. Shipped Harness tools remain available because they are part of the Harness treatment.
- OpenCode starts in pure mode with sharing and auto-update disabled.
- NanoBot `0.1.5.post3` is retained as a historical temporal-proxy image. Its OAuth token is seeded independently; host NanoBot and Codex configuration are never mounted.
- Codex `0.147.0` uses OpenAI's checksum-verified Linux release binary. Its trial home is ephemeral and only the isolated `auth.json` is imported.
- Hermes `0.20.0` is built from tag `v2026.8.3` at its exact Git commit using the release's hash-locked `uv.lock`; safe mode excludes host plugins, memories, rules, and MCP configuration.
- The controller captures native output, control observations, repository status, tracked and untracked changes, evaluator results, timing, and cleanup proof.

## One-time host setup

Start Podman or Docker/Colima, then build the six local images. Podman is the
documented local path; replace `podman` with `docker` on hosts that use Docker:

```text
podman machine start
python3 tools/clean-room.py --runtime podman build
python3 tools/clean-room.py --runtime podman doctor
```

The build verifies the published OMP, OpenCode, Codex, and `uv` binary
checksums, verifies Hermes's exact source commit and locked dependency graph,
verifies the pinned NanoBot Python package version, and writes
`.highlander/images.lock.json`. That file is machine-local because image IDs
are content and platform specific. Match generation copies those IDs into the
Match specification; tags are never accepted by MatchRunner.

Create one clean subscription seed per Harness:

```text
python3 tools/clean-room.py --runtime podman seed omp omp-subscription
python3 tools/clean-room.py --runtime podman seed opencode opencode-subscription
python3 tools/clean-room.py --runtime podman seed codex codex-subscription
python3 tools/clean-room.py --runtime podman seed hermes hermes-subscription
python3 tools/clean-room.py --runtime podman seed nanobot nanobot-subscription
```

Complete the provider login in each disposable container and exit. Seeds
default to `~/.config/highlander/seeds`; set `HIGHLANDER_SEED_ROOT` to relocate
them. A Trial imports only OMP's `agent.db`, OpenCode's `auth.json`, Codex's
`auth.json`, Hermes's independent `auth.json`, or NanoBot/oauth-cli-kit's
`oauth.json` into its temporary home. It never mounts the normal host Harness
directories. Codex uses device authorization with file-based credential
storage. Hermes obtains a separate device-code grant instead of sharing
Codex's rotating refresh token.

OMP's SQLite store can include provider backoff state in addition to credentials. Subscription-backed results must therefore remain in the subscription-realism lane unless stronger routing proof is captured.

## Generate the first Match

Use an exact model identifier supported through the same provider route in both Harnesses:

```text
python3 tools/clean-room.py --runtime podman new-match \
  --match-id linewatch-id-whitespace-r1 \
  --arena ../highlander-arena \
  --base-ref agent/seed-linewatch \
  --task tasks/T002-linewatch-alarm-id-whitespace.md \
  --model PROVIDER/EXACT-MODEL-ID \
  --upstream-model PROVIDER/EXACT-UPSTREAM-ID \
  --provider SAME-PROVIDER \
  --endpoint SAME-ENDPOINT \
  --region SAME-REGION \
  --reasoning low \
  --wire-reasoning PROVIDER-LOW-VALUE \
  --session tmux \
  --output .highlander/matches/linewatch-id-whitespace-r1.json
```

The generator includes the controller-only T002 evaluator overlay and the same `go test`, race, and vet commands for both Contenders.

## Review and run

```text
python3 tools/highlander.py doctor .highlander/matches/linewatch-id-whitespace-r1.json

python3 tools/highlander.py run \
  .highlander/matches/linewatch-id-whitespace-r1.json \
  --save-plan .highlander/plans/linewatch-id-whitespace-r1.json

python3 tools/highlander.py run \
  .highlander/matches/linewatch-id-whitespace-r1.json \
  --plan .highlander/plans/linewatch-id-whitespace-r1.json \
  --execute
```

Review the saved plan before `--execute`. It must show:

- `arena.isolation = independent_disposable_clone`;
- verified image IDs for all five Harnesses and the evaluator;
- `publication_available = false` and `host_home_mounted = false`;
- the intended seed profile names, resources, model controls, Task hash, evaluator-overlay hash, and commands;
- no host Harness configuration paths or credential values.

The tmux Session Adapter launches all workers, waits until every Trial is armed, and releases one filesystem start gate. Same-account subscription throttling can still couple simultaneous Trials, so repeat scored comparisons in randomized matched rounds.

## Result interpretation

The raw result lives under the configured output root:

```text
<match>/trials/<contender>/attempt-001/
├── native/harness-output.jsonl
├── native/container-execution.json
├── repository/diff.patch
├── repository/status.txt
├── validation/summary.json
├── configured-control.json
├── runtime-control.json
├── provider-control.json
├── cleanup.json
└── outcome.json
```

`validation/summary.json` reports the controller evaluator, not tests claimed in the Harness final answer. Hidden evaluator files are overlaid only into a disposable post-Trial copy and cannot appear in the raw patch.

Configured control proves what Highlander requested. Runtime and provider proofs are conservative: if a native event stream does not expose enough identity fields, Highlander marks the Trial invalid for strict attribution rather than guessing. The raw patch and evaluator evidence remain available for debugging that adapter gap.

## Current boundary

The MatchRunner execution path supports clean-core OMP, OpenCode, Codex,
Hermes, and NanoBot on Linux containers. The six ARM64 images and their exact
local IDs passed the Podman doctor on 2026-08-09. The pilot Match
`.highlander/matches/five-harness-login-gate-r1.json` is intentionally blocked
until all five isolated subscription seeds exist. No host Harness login is a
substitute for those seeds. Production-stack and plugin-ablation Matches need
separately labeled images and manifests.

Podman exposes local image IDs as bare 64-character hashes while Docker often
returns the `sha256:` form. Highlander normalizes that runtime representation at
the OCI boundary and always serializes the explicit `sha256:` form required by
the Match schema.
Native macOS Accessibility or AppKit behavior, including full Neru
qualification, requires a disposable macOS VM rather than this Linux clean
room.
