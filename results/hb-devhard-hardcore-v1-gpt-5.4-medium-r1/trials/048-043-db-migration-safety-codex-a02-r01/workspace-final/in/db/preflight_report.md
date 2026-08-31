# Preflight Report

Date: 2026-08-31

## Existing dirty email rows before migration

- Duplicate email: `ada@example.com` is used by `u1` and `u4`.
- Null email: `u5` has `NULL`.
- Blank email: `u6` has `''`.

## Required deterministic cleanup

- Keep `u1` as `ada@example.com`.
- Rewrite `u4` to `ada+u4@example.com`.
- Rewrite `u5` to `missing+u5@example.invalid`.
- Rewrite `u6` to `missing+u6@example.invalid`.

## Dependent orders that must be preserved

- `u4` has dependent order `o2`.
- `u5` has dependent order `o3`.
- `u6` has dependent order `o4`.

## Risk summary

The original draft was unsafe because dropping and recreating `users` without copying rows would lose all users and orphan dependent order data. The replacement migration rebuilds `users` inside a transaction after staging cleaned source rows.
