# Preflight report

Source: `schema.sql`

## Dirty email findings before migration

The existing `users` data contains three dirty email cases that would violate the target constraints:

- Duplicate email: `u1` and `u4` both use `ada@example.com`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

## Required deterministic cleanup

To preserve all users while making `users.email` unique and non-null for the migrated schema:

- Keep `u1` as `ada@example.com`.
- Rewrite `u4` to `ada+u4@example.com`.
- Rewrite `u5` to `missing+u5@example.invalid`.
- Rewrite `u6` to `missing+u6@example.invalid`.

## Dependent orders that must be preserved

Dirty users have existing dependent `orders` rows and must not be deleted or remapped:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

The migration must preserve all user rows, all order rows, and each order's existing `user_id` reference.