# Preflight Report

## Dirty user emails before migration

- Duplicate email: `ada@example.com` is present for `u1` and `u4`.
- Null email: `u5` has `email = NULL`.
- Blank email: `u6` has `email = ''`.

## Dependent orders for dirty users

- `u4` has dependent order `o2`.
- `u5` has dependent order `o3`.
- `u6` has dependent order `o4`.

## Planned cleanup

- Keep `u1` as `ada@example.com`.
- Rewrite `u4` to `ada+u4@example.com`.
- Rewrite `u5` to `missing+u5@example.invalid`.
- Rewrite `u6` to `missing+u6@example.invalid`.
- Preserve all user ids, historical `created_at` values, and all `orders.user_id` references.
