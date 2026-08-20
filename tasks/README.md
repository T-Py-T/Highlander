# Task Authoring

Each task must be independently runnable from a frozen repository snapshot.

`T002-linewatch-alarm-id-whitespace.md` is the first disposable-container Arena task. Its controller-only regression tests live under `evaluators/T002-linewatch-alarm-id-whitespace/` and are applied after each raw Trial.

## Required sections

- Task ID and version.
- Target path or repository.
- Visible problem statement.
- Acceptance criteria.
- Allowed scope.
- Expected validation commands.
- Evaluator-only checks.
- Known ambiguity and the correct escalation boundary.
- Domain and risk classification.

## Task quality rules

- The visible prompt must be sufficient for a competent engineer.
- Hidden tests must check behavior reasonably inferable from the prompt.
- A gold patch is one valid implementation, not the only acceptable shape.
- Tests must not reward formatting, agent verbosity, or use of a particular tool.
- Do not include secrets, production endpoints, or proprietary source.
- Every task must specify how a failed or blocked run is scored.
