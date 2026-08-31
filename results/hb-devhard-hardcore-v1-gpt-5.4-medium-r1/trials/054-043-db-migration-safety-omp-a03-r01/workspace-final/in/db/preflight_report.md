# Preflight Report

## Dirty email findings before migration

The source `users` table contains three email data-quality violations that block a `NOT NULL UNIQUE` email constraint:

- Duplicate email: `u1` and `u4` both use `ada@example.com`. Per policy, `u1` stays unchanged and `u4` is remapped to `ada+u4@example.com`.
- Null email: `u5.email` is `NULL`. It is remapped to `missing+u5@example.invalid`.
- Blank email: `u6.email` is the empty string. It is remapped to `missing+u6@example.invalid`.

## Dependent orders tied to dirty users

Dirty users have dependent order rows that must keep the same `user_id` references after migration:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

## Preservation requirements

- Preserve all six existing user rows.
- Preserve all four existing order rows.
- Preserve each order's existing `user_id`.
- Preserve historical `users.created_at` values during the rebuild.
