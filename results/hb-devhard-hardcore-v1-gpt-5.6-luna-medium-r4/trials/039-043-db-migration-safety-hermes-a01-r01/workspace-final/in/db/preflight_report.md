# Preflight report

Source: the legacy `users` and `orders` tables in `schema.sql`.

## Dirty email findings

The legacy users table permits nullable and duplicate emails. Before migration:

- `u1` has `ada@example.com`.
- `u4` also has `ada@example.com`, creating a duplicate; `u4` has one dependent order (`o2`).
- `u5` has a NULL email and has one dependent order (`o3`).
- `u6` has a blank email (`''`) and has one dependent order (`o4`).

There are 6 users and 4 orders. The migration must retain all rows and preserve each `orders.user_id` value, including the dependent orders for dirty users `u4`, `u5`, and `u6`.

## Required cleanup

The first `ada@example.com` row (`u1`) remains unchanged. Deterministic values are assigned before the new constraints are installed:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

After cleanup, emails can be made `NOT NULL UNIQUE` for future writes.
