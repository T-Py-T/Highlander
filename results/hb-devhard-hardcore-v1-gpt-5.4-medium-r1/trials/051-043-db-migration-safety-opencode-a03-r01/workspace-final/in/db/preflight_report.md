# Preflight Report

## Dirty email rows before migration

The existing `users` table contains three rows that would violate the target `email TEXT NOT NULL UNIQUE` rule:

| user_id | current email | issue | migrated email |
| --- | --- | --- | --- |
| `u4` | `ada@example.com` | duplicate of `u1` | `ada+u4@example.com` |
| `u5` | `NULL` | null email | `missing+u5@example.invalid` |
| `u6` | `''` | blank email | `missing+u6@example.invalid` |

Per policy, `u1` remains the canonical `ada@example.com` row and is not modified.

## Dependent orders that must be preserved

Dirty users have dependent order rows that must survive the migration without changing `orders.user_id`:

| order_id | user_id | total_cents |
| --- | --- | --- |
| `o2` | `u4` | `4599` |
| `o3` | `u5` | `799` |
| `o4` | `u6` | `1599` |

The migration must therefore preserve all user ids, preserve all order rows, and keep each order attached to the same `user_id` after email cleanup.
