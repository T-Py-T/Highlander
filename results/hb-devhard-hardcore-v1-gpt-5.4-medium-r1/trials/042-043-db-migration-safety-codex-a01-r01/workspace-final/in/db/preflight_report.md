# Preflight Report

## Summary

The legacy `users` table contains 6 rows before migration. Three rows have dirty email data that will violate the target `NOT NULL`, `UNIQUE`, and non-blank requirements for future writes.

## Dirty Email Findings

- Duplicate email: `ada@example.com` appears on `u1` and `u4`.
- Null email: `u5.email` is `NULL`.
- Blank email: `u6.email` is `''`.

## Required Deterministic Cleanup

- Keep `u1` unchanged as `ada@example.com`.
- Rewrite `u4.email` to `ada+u4@example.com`.
- Rewrite `u5.email` to `missing+u5@example.invalid`.
- Rewrite `u6.email` to `missing+u6@example.invalid`.

## Dependent Orders

Dirty users have dependent orders that must be preserved with the same `user_id` values:

- `u4` has order `o2`.
- `u5` has order `o3`.
- `u6` has order `o4`.
