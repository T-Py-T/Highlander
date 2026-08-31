# Preflight report

The source schema contains 6 users and 4 orders.

Dirty email findings before migration:

- `ada@example.com` is duplicated by `u1` and `u4`. Per policy, `u1` is the first/retained address and `u4` is cleaned to `ada+u4@example.com`.
- `u5.email` is `NULL`; it is cleaned to `missing+u5@example.invalid`.
- `u6.email` is blank (`''`); it is cleaned to `missing+u6@example.invalid`.

Dependent-order review:

- `u4` has dependent order `o2`.
- `u5` has dependent order `o3`.
- `u6` has dependent order `o4`.

The migration must retain all six user ids, all four order ids, and each order's original `user_id` value. Cleanup changes only the dirty email values; names and historical `created_at` values are retained.
