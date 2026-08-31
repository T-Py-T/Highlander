# Preflight Report

## Email issues before migration

The source `users` table permits nullable and duplicate email values. Before migration:

- `u1` and `u4` both contain `ada@example.com`; `u1` is the first row and remains unchanged, while `u4` is dirty duplicate data.
- `u5` has a `NULL` email.
- `u6` has a blank email (`''`).

## Dependent data

The `orders` table contains dependent rows for every dirty user:

- `o2` references `u4`.
- `o3` references `u5`.
- `o4` references `u6`.

The migration must preserve these order rows and their unchanged `user_id` values while rebuilding `users`.
