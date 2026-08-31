# Preflight Report

## Findings before migration

The legacy `users` table permits nullable and non-unique email values. The input data contains:

- Duplicate `ada@example.com`: `u1` (the retained first row) and `u4`.
- Null email: `u5`.
- Blank email: `u6`.

Dirty users have dependent orders that must remain attached to their original IDs: `u4` → `o2`, `u5` → `o3`, and `u6` → `o4` (as defined by the input schema).

## Required cleanup

The migration preserves every user and order. It keeps `u1` unchanged, changes `u4` to `ada+u4@example.com`, changes `u5` to `missing+u5@example.invalid`, and changes `u6` to `missing+u6@example.invalid`. IDs are not remapped, so dependent `orders.user_id` values remain unchanged.
