# Preflight Report

## Dirty Email Findings

The current `users` data contains three email issues that would violate the target constraints:

- Duplicate email: `u4` duplicates `u1` with `ada@example.com`.
- Null email: `u5` has `NULL` for `email`.
- Blank email: `u6` has an empty string for `email`.

## Required Deterministic Cleanup

The migration must preserve all users and rewrite only the dirty email values as follows:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

The first valid `ada@example.com` row, `u1`, remains unchanged.

## Dependent Orders That Must Be Preserved

Dirty users have dependent orders that must survive the migration with the same `user_id` values:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

Because of those dependencies, the migration must copy data into rebuilt tables instead of deleting or re-keying users.
