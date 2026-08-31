# Migration report

## Strategy

`migration.sql` runs in one explicit `BEGIN IMMEDIATE` transaction. It renames both `users` and its dependent `orders`, creates the constrained users table, copies users, creates orders with its foreign key, copies every order, then drops the old tables and commits. Historical `created_at`, user ids, order ids, totals, and `orders.user_id` values are copied unchanged.

## Dirty-data cleanup

The first `ada@example.com` row (`u1`) stays unchanged. The duplicate `u4` becomes `ada+u4@example.com`; null `u5` becomes `missing+u5@example.invalid`; blank `u6` becomes `missing+u6@example.invalid`. The new users table declares `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`.

## Idempotency

A second run repeats the rebuild against the already-clean users and orders tables. The same ids are copied once into newly created tables, with no append or duplicate operation, and the deterministic cleanup values remain unchanged. The whole operation rolls back on any failure.

## Rollback behavior and limitation

`rollback.sql` uses the same dependent-table copy order and restores users to `id, email, name, created_at`, while retaining all users and orders. It cannot reconstruct the original dirty email values after migration because cleanup is lossy; it retains the migrated deterministic values. Status is intentionally removed.

## Postcheck

Run `postcheck.sql` after migration. The first two queries must return 6 users and 4 orders. All subsequent count queries must return 0. The listed constraint probes should fail with NOT NULL and UNIQUE errors (run each in a transaction and roll it back).
