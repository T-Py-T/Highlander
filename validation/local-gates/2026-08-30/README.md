# 2026-08-30 frozen season validation

This directory records the quota-free validation run for protocol
`hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r1` before any qualification or
scored model calls.

- Protocol SHA-256: `127cc0ce09bce562e7cad2ba86c967d179f31a26b4ed415952a605b797007d21`
- Runner implementation commit: `3b9bfc2aafcf40b0db03c9b4480c559dae62453f`
- Pre-commit result: passed; 48 tests passed, 2 environment-dependent tests
  skipped, and both retained evidence manifests verified.
- Initial doctor result: all six images and versions verified; OMP, OpenCode,
  Codex, and Hermes seeds available; Atomic and NanoBot unavailable.
- Final auth doctor result: all six images and versions verified and all six
  auth-only seeds available; `ready_for_qualification` is true.
- Model calls at these initial gates: none.
- Invalid r1 qualification: six model calls were made; all six rows were
  rejected by the controller because the frozen protocol omitted
  `expected_runtime_reasoning`. No outcome score was produced.
- Corrected protocol: `hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r2`, SHA-256
  `2a767f854595dfed6e1459daace57338628f8d48f3658adcb91b87f29a0c426c`.
  It preserves the same tasks, harnesses, schedule, images, model, and reasoning
  lane while adding the missing frozen control field.
- R2 qualification: OMP, Hermes, Atomic, and NanoBot qualified; OpenCode and
  Codex were unavailable after root-owned image paths blocked their isolated
  auth copy. No scored call ran.
- Current protocol: `hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r3`, SHA-256
  `3c116fcecca9e63076df671b78be14703556b4bc66d11513001b11dd247df76b`.
  It preserves the complete r2 matrix and controls and scopes every home/XDG
  path below a fresh writable tmpfs child.

Artifacts:

- `pre-commit-protocol.log` — complete verbose pre-commit output.
- `season-doctor.log` — exact no-model route-readiness report.
- `season-doctor-all-auth.log` — exact no-model report after Atomic and NanoBot
  authorization completed.
- `season-doctor-r2.log` — exact no-model report for the corrected protocol.
- `pre-commit-r2.log` — complete verbose local gate after the regression fix
  and r2 freeze.
- `season-doctor-r3.log` — exact no-model report for the current protocol.
- `pre-commit-r3.log` — complete verbose local gate after the writable-home
  regression fix and r3 freeze.

The initially unavailable lanes were not assigned zero scores. Qualification
and scoring remained blocked until clean auth-only seeds existed for Atomic
and NanoBot.
