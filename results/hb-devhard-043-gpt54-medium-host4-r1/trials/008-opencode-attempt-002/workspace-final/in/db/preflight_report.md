# Preflight Report

## Dirty user emails before migration

| User ID | Current email | Issue | Planned cleanup |
| --- | --- | --- | --- |
| `u1` | `ada@example.com` | First copy of a duplicate email; retained unchanged | Keep `ada@example.com` |
| `u4` | `ada@example.com` | Duplicate of `u1.email` | Set to `ada+u4@example.com` |
| `u5` | `NULL` | Null email blocks a future `NOT NULL` constraint | Set to `missing+u5@example.invalid` |
| `u6` | `` (blank string) | Blank email is invalid for the future constraint and unique enforcement | Set to `missing+u6@example.invalid` |

## Dependent orders for dirty users

| Order ID | User ID | Reason to preserve |
| --- | --- | --- |
| `o2` | `u4` | Confirms the duplicate-email user keeps the same `users.id` after cleanup |
| `o3` | `u5` | Confirms the null-email user keeps the same `users.id` after cleanup |
| `o4` | `u6` | Confirms the blank-email user keeps the same `users.id` after cleanup |

## Migration risk in the original draft

The original draft dropped `users` before copying data into a replacement table. In SQLite that destroys all user rows, loses historical `created_at` values, and breaks dependent `orders.user_id` references.
