# Preflight Report

## Dirty email findings

The legacy `users` data contains three email quality problems that would violate the target `NOT NULL` and `UNIQUE` requirements:

| User id | Legacy email | Issue | Required migrated email |
| --- | --- | --- | --- |
| `u4` | `ada@example.com` | Duplicate of `u1` | `ada+u4@example.com` |
| `u5` | `NULL` | Null email | `missing+u5@example.invalid` |
| `u6` | `''` | Blank email | `missing+u6@example.invalid` |

The canonical `ada@example.com` record that remains unchanged is user `u1`.

## Dependent order impact

Dirty users have dependent orders that must be preserved with the same `user_id` values:

| User id | Order id | Notes |
| --- | --- | --- |
| `u4` | `o2` | Duplicate-email legacy user |
| `u5` | `o3` | Null-email legacy user |
| `u6` | `o4` | Blank-email legacy user |

The migration must therefore copy forward all users, retain the original user ids, and rebuild `orders` only after the replacement `users` table has been populated.
