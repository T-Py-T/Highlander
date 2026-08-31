# Preflight Report

The source schema contains 6 users and 4 orders. Before migration, `users.email` is nullable and has no uniqueness constraint.

Email issues found:

- `u1` and `u4` both use `ada@example.com`; `u1` is the first existing row and remains unchanged, while `u4` is cleaned to `ada+u4@example.com`.
- `u5` has a NULL email and is cleaned to `missing+u5@example.invalid`.
- `u6` has a blank email and is cleaned to `missing+u6@example.invalid`.

Dependent orders that must remain attached to dirty users:

- `o2` references `u4`.
- `o3` references `u5`.
- `o4` references `u6`.

The migration rebuilds users and orders in dependency order, preserving IDs, order `user_id` values, names, totals, and historical timestamps.