# Preflight Report

## Dirty email findings

- `u4` duplicates `u1` with `ada@example.com` and must be rewritten to `ada+u4@example.com`.
- `u5` has a `NULL` email and must be rewritten to `missing+u5@example.invalid`.
- `u6` has a blank email (`''`) and must be rewritten to `missing+u6@example.invalid`.

## Dependent orders for dirty users

- `u4` owns order `o2`.
- `u5` owns order `o3`.
- `u6` owns order `o4`.

These dependent rows require preserving the original `users.id` values during migration so `orders.user_id` references remain valid.
