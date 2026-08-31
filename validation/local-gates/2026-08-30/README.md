# 2026-08-30 frozen season validation

This directory records the quota-free validation run for protocol
`hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r1` before any qualification or
scored model calls.

- Protocol SHA-256: `127cc0ce09bce562e7cad2ba86c967d179f31a26b4ed415952a605b797007d21`
- Runner implementation commit: `3b9bfc2aafcf40b0db03c9b4480c559dae62453f`
- Pre-commit result: passed; 48 tests passed, 2 environment-dependent tests
  skipped, and both retained evidence manifests verified.
- Doctor result: all six images and versions verified; OMP, OpenCode, Codex,
  and Hermes seeds available; Atomic and NanoBot seeds unavailable.
- Model calls: none.

Artifacts:

- `pre-commit-protocol.log` — complete verbose pre-commit output.
- `season-doctor.log` — exact no-model route-readiness report.

The unavailable lanes are not assigned zero scores. Qualification and scoring
remain blocked until clean auth-only seeds exist for Atomic and NanoBot.
