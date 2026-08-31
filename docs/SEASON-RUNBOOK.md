# Reproduce the hard coding and DevOps season

This runbook reproduces Highlander's six-harness extension of the unchanged
HarnessBench tasks. HarnessBench remains responsible for fixture preparation,
prompt rendering, and deterministic outcome scoring. Highlander supplies only
the randomized schedule, disposable harness containers, evidence retention,
aggregation, redaction, and publication checks.

Two frozen model strata use the same nine tasks, six harnesses, and three
attempts per task: 162 scored slots plus six unscored route qualifications.
Process and combined scores are not evaluated.

| Stratum | Protocol | SHA-256 | Published evidence |
|---|---|---|---|
| Historical control | `hb-devhard-hardcore-v1-gpt-5.4-medium-r1` | `1eb2276c21ce20d8dbaca80ff4b555d5d8c6c1263646d95066a451825b82c1ac` | 161/162 current valid slots; five complete harnesses; Atomic 26/27 |
| Successor model | `hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4` | `c0033d61cc3bdc1c30716c3edf6cf8d815f5b96fe17229491c74b1f178fe37df` | 148/162 valid slots; five complete harnesses; Atomic 13/27 |

The GPT-5.4 stratum is the primary comparison with the original HarnessBench
model generation. It is not an exact recreation of the original worker image,
harness version, provider state, or execution date. NanoBot is therefore a
version-pinned temporal proxy. The two Highlander strata must never be pooled.

GPT-5.6 protocols r1–r3 are retained but must not be used. R1's six qualification calls were
invalidated when a missing `expected_runtime_reasoning` field caused a shared
controller `KeyError`. R2 added that control, qualified four lanes, and retained
OpenCode and Codex as unavailable after Podman populated root-owned home paths.
R3 preserves the task bytes, harness field, schedule, images, model lane, and
limits while moving every runtime home/XDG path into a fresh writable tmpfs
child; all six routes replied successfully. R4 retains that exact matrix and
corrects proof classification before scoring: symbolic model-control values are
identity evidence, numeric token counters are not, and partial visibility is not
an observed conflict.

## 1. Pin the benchmark and build the images

Clone HarnessBench outside the tracked Highlander tree and check out the exact
commit recorded in the protocol:

```text
git clone https://github.com/Qihoo360/harness-bench .highlander/upstream/harness-bench
git -C .highlander/upstream/harness-bench checkout --detach 1025086a446653702b80cfb48babbeec35db6b2c
podman machine start
python3 tools/clean-room.py --runtime podman build
python3 tools/clean-room.py --runtime podman doctor
```

The local image IDs are platform-specific. A reproduction is a new image
stratum unless its image IDs, labels, architecture, harness versions, task
bytes, and controller sources match the published protocol.

## 2. Create authentication-only seeds once

Each command opens a disposable container and retains only the named harness's
credential artifact. It does not import the normal harness home, plugins,
extensions, skills, memories, rules, MCP servers, sessions, or project config.

```text
python3 tools/clean-room.py --runtime podman seed omp omp-subscription
python3 tools/clean-room.py --runtime podman seed opencode opencode-subscription
python3 tools/clean-room.py --runtime podman seed codex codex-subscription
python3 tools/clean-room.py --runtime podman seed hermes hermes-subscription
python3 tools/clean-room.py --runtime podman seed atomic atomic-subscription
python3 tools/clean-room.py --runtime podman seed nanobot nanobot-subscription
```

Use a distinct provider grant per harness. Seeds live outside the repository at
`~/.config/highlander/seeds`, are mounted read-only into an ephemeral home, and
can be reused until the provider expires or revokes the grant. Never commit or
cloud-sync them. An unavailable seed is reported as unavailable; it is never a
zero score.

## 3. Verify the frozen protocol without a model call

```text
python3 tools/hb-season.py doctor \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json.sha256 \
  --upstream .highlander/upstream/harness-bench
```

The doctor fails closed on source, manifest, task, upstream, image, or protocol
drift. `ready_for_qualification` becomes true only when all six seed artifacts
exist.

## 4. Qualify all six model routes

Qualification makes one unscored call per harness with a fixed no-tool prompt.
It proves that the configured route accepts the requested model at run time;
native model/provider/reasoning and provider-wire observations are retained
when the harness exposes them. A configured route is never mislabeled as wire
proof.

```text
python3 tools/hb-season.py qualify \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json.sha256 \
  --upstream .highlander/upstream/harness-bench
```

The scored controller refuses to start unless all six rows in the exact
protocol's qualification summary are `qualified`. If historical NanoBot cannot
run GPT-5.6 Luna, freeze a separate temporal-proxy protocol instead of silently
substituting GPT-5.4 or pooling the lane into the same-model ranking.

## 5. Run the hard-first stages

Run attempts sequentially to avoid refresh-token races and shared-subscription
throttling. The controller appends and fsyncs one immutable result row after
each trial, so the same command resumes missing slots. A valid low score is
never retried. An infrastructure-invalid slot is retained and is retried only
with the explicit `--retry-invalid` flag.

```text
python3 tools/hb-season.py run \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json.sha256 \
  --manifest benchmark-packs/hb-devhard-hardcore-v1-r4.json \
  --upstream .highlander/upstream/harness-bench \
  --stage hardest-first

python3 tools/hb-season.py run \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4.json.sha256 \
  --manifest benchmark-packs/hb-devhard-hardcore-v1-r4.json \
  --upstream .highlander/upstream/harness-bench \
  --stage cross-repository-and-diagnostic
```

The first stage is 90 scored calls across the five hardest tasks. The second is
72 calls across four cross-repository and diagnostic tasks. Private raw
evidence is retained below `.highlander/runs/`; containers and temporary
HarnessBench sandboxes are removed after patches, final workspaces, evaluator
payloads, and cleanup proof are captured.

## 6. Export and verify public evidence

Export only from a clean runner commit. The exporter verifies the private
manifest, replaces exact machine roots, rejects common credential patterns,
normalizes process and usage observations without fabricating a process score,
rebuilds the leaderboard from `results.jsonl`, and seals the public copy.

```text
python3 tools/hb-evidence.py export-season \
  --source .highlander/runs/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4-raw \
  --output results/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4

python3 tools/hb-evidence.py verify-season \
  results/hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4
```

## GPT-5.4 matched companion commands

Use the same lifecycle with the GPT-5.4 protocol and companion manifest:

```text
python3 tools/hb-season.py doctor \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json.sha256 \
  --upstream .highlander/upstream/harness-bench

python3 tools/hb-season.py qualify \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json.sha256 \
  --upstream .highlander/upstream/harness-bench

python3 tools/hb-season.py run \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json.sha256 \
  --manifest benchmark-packs/hb-devhard-hardcore-v1-gpt54-r1.json \
  --upstream .highlander/upstream/harness-bench \
  --stage hardest-first

python3 tools/hb-season.py run \
  --protocol protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json \
  --protocol-sha256 protocols/hb-devhard-hardcore-v1-gpt-5.4-medium-r1.json.sha256 \
  --manifest benchmark-packs/hb-devhard-hardcore-v1-gpt54-r1.json \
  --upstream .highlander/upstream/harness-bench \
  --stage cross-repository-and-diagnostic

python3 tools/hb-evidence.py export-season \
  --source .highlander/runs/hb-devhard-hardcore-v1-gpt-5.4-medium-r1-raw \
  --output results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1

python3 tools/hb-evidence.py verify-season \
  results/hb-devhard-hardcore-v1-gpt-5.4-medium-r1
```

The retained Highlander run used `--retry-invalid` only after a documented
pre-model authorization or container failure. Valid low scores were never
retried. Every replacement remains in `results.jsonl`; aggregation selects the
latest row for each frozen slot. The final unresolved Atomic CLI-parser slot
timed out twice at the exact 1,200-second wall limit and remains invalid rather
than becoming a zero or being retried until favorable.

Before a pull request, run `pre-commit run --all-files --verbose` and
`tools/run-act-local.sh`. Public visibility is the final operation, after the
result bundle, README table, issue trail, privacy scan, clean-checkout
verification, and local workflow all pass.

## What is and is not comparable

- Outcome scores, per-task means and ranges, reliability, invalid counts, and
  elapsed time come from the retained fixed matrix.
- Tool and usage records explain harness behavior but native event and token
  semantics differ; they are not folded into correctness.
- NanoBot is the pinned historical temporal proxy used to connect this season
  to the original HarnessBench landscape. It is not an exact reproduction of
  the unpublished historical environment.
- A contender missing any fixed slot is visible but unranked. Complete
  contenders may be ranked in a provisional season while the incomplete lane
  remains explicit.
