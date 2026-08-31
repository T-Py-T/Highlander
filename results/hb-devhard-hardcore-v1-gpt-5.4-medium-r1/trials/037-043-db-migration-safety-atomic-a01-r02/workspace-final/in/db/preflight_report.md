# Preflight report

## Dirty email rows before migration

The source `users` table has 6 rows. Three rows need cleanup before a unique, non-null email constraint can be enforced.

- `u4` duplicates `u1` with `ada@example.com`.
- `u5` has `NULL` for `email`.
- `u6` has a blank `email` value: `''`.

## Dependent orders tied to dirty users

Dirty users have live order rows that must keep the same `user_id` values.

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

## Required cleanup mapping

The migration must preserve every user row and rewrite only the bad email values below.

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`u1`, `u2`, and `u3` keep their existing emails.
