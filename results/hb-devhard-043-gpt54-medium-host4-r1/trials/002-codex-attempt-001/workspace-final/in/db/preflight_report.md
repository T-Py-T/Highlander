# Preflight Report

## Dirty email rows before migration

The legacy `users.email` column allows nullable and duplicate values.

Affected users:

| user_id | current email | issue |
| --- | --- | --- |
| `u4` | `ada@example.com` | Duplicate of `u1`; must migrate to `ada+u4@example.com` |
| `u5` | `NULL` | Null email; must migrate to `missing+u5@example.invalid` |
| `u6` | `''` | Blank email; must migrate to `missing+u6@example.invalid` |

## Dependent orders tied to dirty users

These dependent orders must be preserved with the same `user_id` values:

| order_id | user_id | total_cents |
| --- | --- | --- |
| `o2` | `u4` | `4599` |
| `o3` | `u5` | `799` |
| `o4` | `u6` | `1599` |

The migration therefore has to rebuild `users` without deleting or re-keying those legacy users.
