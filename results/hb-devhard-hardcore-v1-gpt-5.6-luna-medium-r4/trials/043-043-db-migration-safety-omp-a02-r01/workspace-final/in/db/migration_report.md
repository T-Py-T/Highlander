# Migration Report

## Strategy

`migration.sql` runs in one explicit transaction. It renames `orders` before `users`, rebuilds `users` with `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`, copies users, rebuilds orders with its foreign key, then drops the temporary tables and restores the original table names. This dependency order keeps every `orders.user_id` reference valid and preserves historical `created_at` values.

## Dirty-data cleanup

The copy is deterministic: `u4` becomes `ada+u4@example.com`, `u5` becomes `missing+u5@example.invalid`, and `u6` becomes `missing+u6@example.invalid`. Existing clean emails are copied unchanged. The cleanup allows the new non-null unique constraint to be created without deleting users.

## Idempotency

A second run repeats the same transactional rebuild from the already-migrated tables. The cleanup mappings produce the same values, and each copy inserts exactly one row per source row; no users or orders are duplicated.

## Rollback behavior and limitation

`rollback.sql` is executable after migration and performs the same dependency-safe rebuild, restoring the old users shape (`id`, `email`, `name`, `created_at`) while preserving users and orders. It intentionally retains the deterministic cleaned email values: the old schema has no audit column from which the original NULL, blank, or duplicate values could be reconstructed. A failed migration transaction rolls back atomically.

## Postcheck

Run `postcheck.sql` against the migrated database. It reports user/order counts, order-to-user mismatches, dirty-user email mismatches, null/blank/duplicate email counts, status violations, and the `users` column/index metadata proving the NOT NULL and UNIQUE constraints.