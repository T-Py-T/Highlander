# Preflight report

## Dirty email rows before migration

The current `users` data has three email problems:

- Duplicate email: `u4` duplicates `u1` with `ada@example.com`.
- Null email: `u5` has `NULL` email.
- Blank email: `u6` has an empty-string email.

## Dependent orders tied to dirty users

These dirty users already have dependent `orders` rows, so the migration must preserve user ids and order references:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

## Required cleanup mapping

The migration must keep every user row and rewrite only the unsafe emails:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`created_at` values and all `orders.user_id` references must stay unchanged.
