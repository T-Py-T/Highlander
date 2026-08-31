# Migration Report

## Strategy

`migration.sql` disables foreign-key enforcement before an explicit `BEGIN IMMEDIATE`, normalizes dirty emails, copies users into a canonical table, swaps the table, commits, and re-enables foreign keys. Orders are never rewritten, so their IDs and `user_id` values remain unchanged. Historical `created_at` values are copied directly.

## Dirty-data cleanup

- `u4`: `ada@example.com` -> `ada+u4@example.com` (the first `ada@example.com` row, `u1`, is unchanged).
- `u5`: `NULL` -> `missing+u5@example.invalid`.
- `u6`: blank -> `missing+u6@example.invalid`.

The destination declares `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`, enforcing the future-write requirements.

## Idempotency

A second execution repeats the deterministic updates and rebuilds the same canonical users rows without inserting duplicate user or order rows. The script is intended for the supplied schema and canonical migration shape; it assigns `active` to every copied row on each run.

## Rollback behavior and limitation

Run `rollback.sql` after migration. It rebuilds `users` with exactly `id`, `email`, `name`, and `created_at`, while preserving all rows and orders. Because no pre-migration email history is stored, rollback preserves the cleaned email values; it cannot reconstruct the original duplicate, `NULL`, or blank values.

## Postcheck

Run `postcheck.sql` after migration. It checks user/order counts, the three dirty-user order references, deterministic cleaned emails, null/blank and duplicate violations, status nullability at the data level, and the `users` table/index/column declarations.
