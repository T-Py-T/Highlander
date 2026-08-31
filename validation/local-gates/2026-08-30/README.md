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
- Model calls: none.

Artifacts:

- `pre-commit-protocol.log` — complete verbose pre-commit output.
- `season-doctor.log` — exact no-model route-readiness report.
- `season-doctor-all-auth.log` — exact no-model report after Atomic and NanoBot
  authorization completed.

The initially unavailable lanes were not assigned zero scores. Qualification
and scoring remained blocked until clean auth-only seeds existed for Atomic
and NanoBot.
