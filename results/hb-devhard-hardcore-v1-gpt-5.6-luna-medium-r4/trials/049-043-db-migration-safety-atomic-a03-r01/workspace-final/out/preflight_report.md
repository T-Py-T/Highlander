# Migration preflight report

## Source inventory

The supplied schema contains 6 users and 4 orders. The migration must retain every row, each `orders.user_id` reference, and each historical `created_at` value.

## Email issues and deterministic cleanup

| Issue | Affected user(s) | Required migration result |
|---|---|---|
| Duplicate `ada@example.com` (2 rows) | `u1`, `u4` | Keep `u1` as `ada@example.com`; change `u4` to `ada+u4@example.com`. |
| NULL email (1 row) | `u5` | Change `u5` to `missing+u5@example.invalid`. |
| Blank email (1 row, the empty string) | `u6` | Change `u6` to `missing+u6@example.invalid`. |

No other email value requires normalization or rewriting.

## Dependent orders

The dirty-email users cannot be deleted or assigned new ids because orders depend on their existing ids:

- Order `o2` references user `u4`.
- Order `o3` references user `u5`.
- Order `o4` references user `u6`.

The migration therefore rebuilds the users table by copying rows with the same user ids, changing only the three required email values and adding the default `active` status.
