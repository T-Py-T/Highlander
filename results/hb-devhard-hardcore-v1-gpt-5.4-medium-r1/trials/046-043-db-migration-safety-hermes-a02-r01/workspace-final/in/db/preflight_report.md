# Preflight report

## Source data issues detected before migration

The current `users` table contains 6 rows and has three dirty email cases that block adding `NOT NULL` and `UNIQUE` constraints directly:

- Duplicate email: `ada@example.com` appears for `u1` and `u4`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

## Deterministic cleanup required by migration

To preserve every user row while making `users.email` unique and non-null for future writes, the migration assigns these exact values:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

The first existing `ada@example.com` row (`u1`) remains unchanged.

## Dependent orders that must be preserved

Dirty users have dependent `orders` rows and therefore cannot be dropped or replaced with new ids:

- `u4` is referenced by order `o2`.
- `u5` is referenced by order `o3`.
- `u6` is referenced by order `o4`.

The migration must preserve all existing order rows and keep each `orders.user_id` pointing at the same user id after cleanup.
