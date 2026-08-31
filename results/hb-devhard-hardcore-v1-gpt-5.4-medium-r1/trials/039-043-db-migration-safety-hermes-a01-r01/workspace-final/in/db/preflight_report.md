# Preflight report

Source snapshot before migration:
- users row count: 6
- orders row count: 4

Dirty email findings:
- Duplicate email: `ada@example.com` appears on `u1` and `u4`.
- Null email: `u5` has `NULL` email.
- Blank email: `u6` has an empty-string email.

Required deterministic cleanup before enforcing `NOT NULL` + `UNIQUE` for future writes:
- Keep `u1` as `ada@example.com`.
- Change duplicate `u4` to `ada+u4@example.com`.
- Change null-email `u5` to `missing+u5@example.invalid`.
- Change blank-email `u6` to `missing+u6@example.invalid`.

Dependent orders that must be preserved for dirty users:
- `u4` has dependent order `o2`.
- `u5` has dependent order `o3`.
- `u6` has dependent order `o4`.

Migration safety expectations:
- Preserve all 6 users.
- Preserve all 4 orders.
- Preserve `orders.user_id` values, especially for `u4`, `u5`, and `u6`.
- Preserve historical `created_at` values while adding `users.status TEXT NOT NULL DEFAULT 'active'`.
