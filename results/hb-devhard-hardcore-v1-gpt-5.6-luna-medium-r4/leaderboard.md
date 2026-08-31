# hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4

Status: **provisional**

| Rank | Harness | Overall | Best/task | Mean | Median | Worst/task | Zero | Stddev | Invalid | Valid |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | omp | 0.9026 | 0.9294 | 0.9026 | 0.9452 | 0.8822 | 0.0000 | 0.1031 | 0 | 27/27 |
| 2 | hermes | 0.8960 | 0.9025 | 0.8960 | 0.9288 | 0.8878 | 0.0000 | 0.1084 | 0 | 27/27 |
| 3 | opencode | 0.8941 | 0.8963 | 0.8941 | 0.9428 | 0.8917 | 0.0000 | 0.1105 | 0 | 27/27 |
| 4 | nanobot | 0.2673 | 0.2719 | 0.2673 | 0.1928 | 0.2644 | 0.0000 | 0.2375 | 0 | 27/27 |
| 5 | codex | 0.1801 | 0.1801 | 0.1801 | 0.1837 | 0.1801 | 0.0000 | 0.0775 | 0 | 27/27 |
| — | atomic | 0.8649 | 0.9028 | 0.8323 | 0.8843 | 0.7915 | 0.0000 | 0.2201 | 14 | 13/27 |

Overall follows the frozen primary rule `mean_of_per_task_mean_valid_outcome`. Incomplete contenders are shown but never ranked.

## Per-task outcome scores

Each cell is the task mean followed by the worst–best attempt range. A single value means all valid attempts matched.

| Task | omp | hermes | opencode | nanobot | codex | atomic |
|---|---:|---:|---:|---:|---:|---:|
| 039-repo-architecture-map | 0.9321 (0.8923–0.9588) | 0.9430 (0.9288–0.9573) | 0.9403 (0.9323–0.9457) | 0.9045 (0.8783–0.9457) | 0.1200 | 0.6237 (0.1200–0.8843) |
| 042-api-schema-migration | 0.7400 | 0.7400 | 0.7400 | 0.1500 | 0.1500 | 0.7400 |
| 043-db-migration-safety | 0.9670 (0.9270–0.9870) | 0.9670 (0.9270–0.9870) | 0.9870 | 0.0980 | 0.0980 | 0.9870 |
| 064-service-dependency-triage | 0.8222 | 0.8322 (0.8222–0.8372) | 0.8222 | 0.0600 | 0.0600 | 0.8172 (0.8072–0.8222) |
| 086-sql-migration-preflight-rollback | 0.7902 (0.7000–0.9706) | 0.7000 | 0.7000 | 0.1928 | 0.1928 | — |
| 083-monorepo-interface-repair | 1.0000 | 1.0000 | 1.0000 | 0.2300 | 0.2300 | — |
| 085-flaky-test-root-cause | 1.0000 | 1.0000 | 1.0000 | 0.1837 | 0.1837 | 1.0000 |
| 082-compose-config-repair | 0.9900 | 0.9900 | 0.9900 | 0.3000 | 0.3000 | 0.9900 |
| 087-cli-parser-bug-tests | 0.8821 (0.8679–0.8964) | 0.8916 (0.8821–0.9107) | 0.8679 (0.8536–0.8821) | 0.2867 | 0.2867 | 0.8964 |
