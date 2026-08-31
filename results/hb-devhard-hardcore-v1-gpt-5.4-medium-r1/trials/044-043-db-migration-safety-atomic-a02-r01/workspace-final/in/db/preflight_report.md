# Preflight report

## Dirty email rows before migration

| user_id | original email | issue | migrated email |
| --- | --- | --- | --- |
| u4 | `ada@example.com` | duplicate of `u1` | `ada+u4@example.com` |
| u5 | `NULL` | null email | `missing+u5@example.invalid` |
| u6 | `''` | blank email | `missing+u6@example.invalid` |

## Summary

- `users` rows before migration: 6
- `orders` rows before migration: 4
- Dirty email rows before migration: 3
- Duplicate email value: `ada@example.com` on `u1` and `u4`
- Null email rows: `u5`
- Blank email rows: `u6`

## Dependent orders for dirty users

- `u4` has dependent order `o2`
- `u5` has dependent order `o3`
- `u6` has dependent order `o4`

These users and order references must be kept during migration.
