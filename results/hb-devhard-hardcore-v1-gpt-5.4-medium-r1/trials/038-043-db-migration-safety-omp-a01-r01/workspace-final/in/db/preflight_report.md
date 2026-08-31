# Preflight Report

## Dirty email rows before migration

- Duplicate email: `u1` and `u4` both use `ada@example.com`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

## Dependent orders for dirty users

- `u4` is referenced by order `o2`.
- `u5` is referenced by order `o3`.
- `u6` is referenced by order `o4`.

## Migration cleanup required

- Keep `u1` as `ada@example.com`.
- Rewrite `u4` to `ada+u4@example.com`.
- Rewrite `u5` to `missing+u5@example.invalid`.
- Rewrite `u6` to `missing+u6@example.invalid`.
- Preserve every user row, every order row, all `orders.user_id` values, and all historical `created_at` values.
