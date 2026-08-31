# Preflight Report

## Summary

The source `users` table contains 6 rows before migration.

Dirty email rows identified before migration:

- Duplicate email: `u1` and `u4` both use `ada@example.com`.
- Null email: `u5` has `NULL` in `email`.
- Blank email: `u6` has an empty-string `email`.

## Dependent Orders

Dirty users with dependent `orders` rows that must be preserved:

- `u4` -> order `o2`
- `u5` -> order `o3`
- `u6` -> order `o4`

These dependencies require a copy-and-swap migration that preserves user ids instead of deleting and reinserting a subset of users.

## Planned Cleanup

The migration applies the required deterministic replacements:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`u1` remains the retained owner of `ada@example.com`.
