# Evidence Bundle contract

An Evidence Bundle is Highlander's public result interface. It must let a reader determine what was controlled, what the harness exposed, what the model and harness actually did, what changed in the Arena, how the result was evaluated, where the operator intervened, and whether cleanup completed.

## Directory contract

```text
<match-id>/
├── match-spec.json
├── execution-plan.json
├── control-profile.json
├── match-result.json
├── artifact-manifest.json
├── task/
│   ├── task.bin
│   └── task.sha256
├── journal/
│   └── match-events.jsonl
├── session/
│   ├── manifest.json
│   └── cleanup.json
└── trials/<contender>/attempt-001/
    ├── trial-plan.json
    ├── capability.json
    ├── invocation.redacted.json
    ├── configured-control.json
    ├── runtime-control.json
    ├── provider-control.json
    ├── events.jsonl
    ├── native/
    │   ├── terminal.log
    │   └── transcript.*
    ├── normalized/
    │   └── trajectory.atif.json
    ├── repository/
    │   ├── base-sha
    │   ├── final-sha
    │   ├── status.txt
    │   └── diff.patch
    ├── validation/
    ├── operator-interactions.jsonl
    ├── cleanup.json
    └── outcome.json
```

The pilot creates the applicable subset and reserves the remaining paths for real coding, validation, and operator evidence. `artifact-manifest.json` hashes retained evidence but intentionally excludes raw worktree contents. The patch and repository inventory are the publishable candidate representation.

Clean-room evaluation copies the completed raw workspace, applies the reviewed evaluator overlay only to that copy, runs every command in the pinned evaluator image, and removes the copy. The overlay hash, command argv, output, duration, exit status, timeout, and cleanup proof are retained under `validation/`. Evaluator files never enter the Harness workspace or contender patch.

## Public export gate

Raw Match directories are machine-local review surfaces. Publish only through the fail-closed exporter:

```text
python3 tools/evidence-bundle.py export \
  --source .highlander/runs/MATCH-ID \
  --output results/MATCH-ID \
  --runner-repository /path/to/clean/highlander-checkout
python3 tools/evidence-bundle.py verify results/MATCH-ID
```

The exporter verifies the sealed source manifest before copying, refuses a dirty runner checkout, copies only manifested files, excludes worktrees and workspaces, replaces machine-local roots with stable placeholders, rejects high-confidence credential patterns, records runner/Arena/Task/plan provenance, and seals the public copy with a new manifest. Existing destinations are immutable; choose a new Match ID instead of editing published evidence in place.

HarnessBench pilot sources use a separate exporter because they retain the
upstream sandbox result, final task workspace, and native CLI streams rather
than a MatchRunner worktree:

```text
python3 tools/hb-evidence.py export \
  --source .highlander/runs/PILOT-ID-raw \
  --output results/PILOT-ID \
  --runner-repository /path/to/clean/highlander-checkout
python3 tools/hb-evidence.py verify results/PILOT-ID
```

That exporter verifies the private and per-Trial manifests, retains native
transcripts, redacts exact machine roots, rejects credential patterns,
normalizes only natively observable usage and tool-start events, keeps process
and combined scores null, records a redaction report and clean runner commit,
and regenerates exact public manifests. Native token and cost accounting stays
explicitly non-comparable across Harnesses.

## Three control proofs

A strict Trial needs all three:

1. `configured-control.json` shows the exact native command/config requested.
2. `runtime-control.json` shows the model, route, reasoning, fallback, and auxiliary calls observed by the Harness.
3. `provider-control.json` shows wire metadata, deployment logs, or an equivalent transparent gateway proof of what was sent and served.

If proof 3 is unavailable, the Trial is provisional. A different main or auxiliary model, fallback provider, reasoning translation, endpoint, region, service tier, or prompt hash invalidates a strict Trial.

## Capability versus usage

`capability.json` is captured before release and declares what the Harness offers: tools, MCP servers, memory, permissions, subagents, native protocol, prompt transport, and known limitations. Native transcripts and ATIF steps record what was actually used. An unused declared capability remains distinct from an absent capability.

## Native and normalized evidence

Native harness output is authoritative. `trajectory.atif.json` is a derived ATIF v1.7 projection for Harbor-compatible analysis and viewers. It must retain provenance to the native file and must not invent tool calls, reasoning, tokens, costs, or model identity that the native protocol did not expose.

When a harness exposes only a terminal transcript, retain it and mark semantic fields unknown. Do not infer a strict model proof, tool call, completion, or cost from terminal appearance alone.

## Qualification and outcome are separate

`qualification=qualified` means the Trial is comparable, not that the code is correct. A harness crash, timeout, failed test, or poor patch can be a qualified competitive failure when controls and evidence remain intact.

`qualification=invalid` means the experiment cannot support a harness claim. Reasons include control divergence, different Task bytes, contamination, missing required evidence, uncertain duplicate submission, or unreconciled processes and resources.

The worker may make a qualification claim, but it is never the authority. After session cleanup, the parent MatchRunner independently reloads every required proof, compares model/provider/reasoning/endpoint/region/fallback/auxiliary fields with the frozen Control Profile, verifies the Task hash and required native/ATIF artifacts, probes the recorded process group, and writes the final qualification.

Execution also requires the exact content-addressed plan produced by dry-run. If the Task, base ref, adapter version, capability probe, Session Adapter, or plan hash changes after review, Highlander stops before creating the Match directory.

## Operator interactions

Real Trials append timestamped records using these categories:

- planned approval;
- appropriate clarification;
- steering;
- rescue;
- manual completion;
- autonomous recovery.

Record active operator time separately from wall time. Do not award autonomy based on silence when the harness was blocked or abandoned.

## Publication and redaction

Public packages must remove credentials, tokens, personal paths, subscription/account identifiers, private repository URLs, proprietary source, active hidden evaluators, and unredacted private prompts. Use stable placeholders so relationships remain inspectable. Record every removed or unavailable artifact explicitly.

Keep tasks and evaluators private while they are active. Publish retired task versions, evaluator logic, all contenders' results, repeat counts, and invalidations together. Controlled API, native subscription-realism, concurrent, and warm-memory Matches use separate labels and leaderboards.
