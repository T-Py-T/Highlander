# Preflight Report

## Dirty user email issues before migration

- Duplicate email: `ada@example.com` is used by `u1` and `u4`.
- Null email: `u5` has `NULL` in `users.email`.
- Blank email: `u6` has an empty-string value in `users.email`.

## Dependent orders that must be preserved

- `u4` has dependent order `o2`.
- `u5` has dependent order `o3`.
- `u6` has dependent order `o4`.

## Required cleanup mapping

- Keep `u1` as `ada@example.com`.
- Rewrite `u4` to `ada+u4@example.com`.
- Rewrite `u5` to `missing+u5@example.invalid`.
- Rewrite `u6` to `missing+u6@example.invalid`.

## Migration risk if handled unsafely

- Dropping and recreating `users` without copying data would remove all users.
- Rebuilding `users` without preserving ids would break `orders.user_id` references.
- Enforcing `NOT NULL` and `UNIQUE` before cleanup would fail on the existing dirty rows.
