# hb-devhard-043-gpt54-medium-host4-r1

Protocol SHA-256: `514cd5958b812ab5c4c6c9e6e84910721cd3294663718ea2c09e601cab06d1d9`

> Claim boundary: one deterministic hard task with three repeats per available host-isolated harness. This pilot does not declare a winner or generalize across tasks.

Process and combined scores were not evaluated. Native process and usage facts are retained separately and are not assumed cross-harness comparable.

| Harness | Trials | Scores | Mean | Population σ | Mean seconds | Observed tool invocations |
|---|---:|---|---:|---:|---:|---:|
| codex | 3 valid / 0 invalid / 0 unavailable | 0.917, 0.27, 0.987 | 0.7247 | 0.3228 | 278.197 | 43 (3/3) |
| hermes | 3 valid / 0 invalid / 0 unavailable | 0.995, 0.995, 0.98 | 0.99 | 0.0071 | 275.101 | — (0/3) |
| nanobot | 0 valid / 0 invalid / 1 unavailable | — | — | — | — | — (0/0) |
| omp | 3 valid / 0 invalid / 0 unavailable | 0.909, 0.909, 0.995 | 0.9377 | 0.0405 | 319.955 | 85 (3/3) |
| opencode | 3 valid / 0 invalid / 0 unavailable | 0.995, 0.995, 0.987 | 0.9923 | 0.0038 | 209.134 | 42 (3/3) |

## Interpretation

- OpenCode and Hermes were highly repeatable on this task; OMP was somewhat lower and more variable.
- Codex completed two excellent solutions but one valid migration failed with a foreign-key error, producing high variance.
- NanoBot was unavailable because no qualified dedicated host OAuth profile existed; it was not scored zero.
- The next highest-evidence run is the same frozen four-harness control across the remaining 11 DevHard tasks, after a clean-room auth lane is requalified or explicitly retained as a separate host stratum.
