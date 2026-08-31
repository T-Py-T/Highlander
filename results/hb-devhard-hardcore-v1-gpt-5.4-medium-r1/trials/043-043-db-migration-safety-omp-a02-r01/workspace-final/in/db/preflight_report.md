# Preflight Report

## Dirty email rows before migration

Source data in `schema.sql` contains three email integrity violations in `users`:

- Duplicate email: `u4` repeats `ada@example.com`, which is already used by `u1`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

These rows cannot satisfy a future `NOT NULL` plus unique email constraint without cleanup.

## Required deterministic cleanup

The migration must preserve the rows and rewrite only the invalid email values to these deterministic values:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`u1` keeps `ada@example.com` unchanged as the first valid holder of that address.

## Dependent orders that must remain attached

Dirty users have dependent orders that must keep the same `user_id` values after migration:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

The migration therefore must preserve user ids and rebuild `users` without deleting or rekeying those rows.
