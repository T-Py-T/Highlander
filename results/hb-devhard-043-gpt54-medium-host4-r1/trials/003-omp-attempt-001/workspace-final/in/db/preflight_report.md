# Preflight report

## Source state
- `users` rows: 6
- `orders` rows: 4
- Existing `users.email` is nullable and not unique.
- Existing `users` schema has no `status` column.

## Dirty email findings
- Duplicate email: `ada@example.com` is present on `u1` and `u4`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

## Required deterministic cleanup
- Keep `u1` unchanged as `ada@example.com`.
- Rewrite duplicate user `u4` to `ada+u4@example.com`.
- Rewrite null-email user `u5` to `missing+u5@example.invalid`.
- Rewrite blank-email user `u6` to `missing+u6@example.invalid`.

## Dependent orders for dirty users
- `u4` is referenced by order `o2`.
- `u5` is referenced by order `o3`.
- `u6` is referenced by order `o4`.

## Migration risk in the draft
- Dropping `users` before copying data would delete all user rows.
- Dependent `orders.user_id` references would be left without their original parent rows.
- Recreating `created_at` with a new default would destroy historical timestamps.
