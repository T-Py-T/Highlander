# Preflight report

Source snapshot reviewed from `schema.sql` before migration.

## Dirty email findings

- Duplicate email: `ada@example.com` appears on users `u1` and `u4`.
- Null email: user `u5` has `NULL` email.
- Blank email: user `u6` has an empty-string email.
- Total dirty user rows requiring cleanup before adding `NOT NULL` + `UNIQUE`: 3 (`u4`, `u5`, `u6`).

## Deterministic cleanup plan

- Keep `u1` as `ada@example.com`.
- Change duplicate `u4` to `ada+u4@example.com`.
- Change null-email `u5` to `missing+u5@example.invalid`.
- Change blank-email `u6` to `missing+u6@example.invalid`.

## Dependent orders that must be preserved

- User `u4` has dependent order `o2`.
- User `u5` has dependent order `o3`.
- User `u6` has dependent order `o4`.

These dependent orders require the migration to preserve the existing `users.id` values so `orders.user_id` continues to reference the same rows after cleanup.
