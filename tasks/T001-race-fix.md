# T001 — Duplicate Completion Event

Version: 1
Domain: traditional software
Risk: medium
Target: `fixtures/job-runner/job_registry.py`

## Task

A background job can remain marked as running after it has already exited when two completion events arrive nearly simultaneously.

Reproduce the defect from the public behavior, identify the root cause, implement the smallest maintainable fix, and add a regression test that fails before the fix. Preserve all unrelated behavior.

Take the task through the harness's normal planning, implementation, test, review, and draft-PR workflow. Do not merge or deploy.

## Acceptance criteria

- A job is marked completed after one completion event.
- Duplicate or concurrent completion events are idempotent.
- An unknown job does not create an invalid record or crash the registry.
- Existing lifecycle behavior remains green.
- A regression test demonstrates the original failure and the fixed behavior.
- The final report includes the exact head SHA and commands actually run.

## Allowed scope

Modify only `fixtures/job-runner/` and the task-specific documentation needed to explain the fix. Do not modify benchmark tooling, scoring, schemas, or evaluator material.

## Evaluator-only checks

- A hidden test sends duplicate completion events from multiple threads.
- A hidden test verifies no “sleep and retry until green” workaround.
- A hidden test verifies the registry does not silently convert completed jobs back to running.
- The evaluator checks that unrelated files remain unchanged.
