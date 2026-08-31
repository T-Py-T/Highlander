# Preflight report

## Summary

The source dataset contains 6 users and 4 orders before migration.

## Dirty email findings before migration

- Duplicate email: `ada@example.com`
  - `u1` keeps `ada@example.com`
  - `u4` is the duplicate row and must be reassigned to `ada+u4@example.com`
- Null email:
  - `u5` has `NULL` email and must be reassigned to `missing+u5@example.invalid`
- Blank email:
  - `u6` has `''` and must be reassigned to `missing+u6@example.invalid`

## Dependent orders tied to dirty users

The following dirty users already have dependent orders, so the migration must preserve user ids and order references:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

## Safety implications

- Do not drop and recreate `users` without copying data first.
- Do not change user ids.
- Do not rewrite `orders.user_id` values.
- Preserve all historical `created_at` values while cleaning only the email field and adding `status`.
