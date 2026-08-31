# Preflight report

The source schema has 6 users and 4 orders.

Before migration, email data is dirty:

- `u1` and `u4` both use `ada@example.com` (duplicate). Per policy, keep `u1` unchanged and migrate `u4` to `ada+u4@example.com`.
- `u5.email` is `NULL`; migrate it to `missing+u5@example.invalid`.
- `u6.email` is blank (`''`); migrate it to `missing+u6@example.invalid`.

Dependent orders must remain attached to the same user ids: dirty user `u4` has order `o2`, `u5` has `o3`, and `u6` has `o4`. The migration copies orders before removing the old users table, so these references remain intact.
