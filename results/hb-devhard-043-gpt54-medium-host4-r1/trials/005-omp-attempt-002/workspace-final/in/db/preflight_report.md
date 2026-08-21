# Preflight report

## Dirty email findings before migration

| User id | Legacy email | Issue | Planned migrated email |
| --- | --- | --- | --- |
| u4 | `ada@example.com` | Duplicate of `u1`; `u1` remains the canonical `ada@example.com` row. | `ada+u4@example.com` |
| u5 | `NULL` | Null email violates the future non-null requirement. | `missing+u5@example.invalid` |
| u6 | `''` | Blank email violates the future non-null requirement. | `missing+u6@example.invalid` |

## Dependent orders tied to dirty users

| User id | Order ids | Order count |
| --- | --- | --- |
| u4 | `o2` | 1 |
| u5 | `o3` | 1 |
| u6 | `o4` | 1 |

These dependent orders require an in-place user migration that preserves the same user ids. Dropping and recreating `users` without copying rows would orphan or lose order relationships.
