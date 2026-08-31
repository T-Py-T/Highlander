# Migration Report

## Strategy

The migration runs in `BEGIN IMMEDIATE`/`COMMIT`. It copies `orders` to a
temporary table, drops the dependent table, rebuilds `users` with `email TEXT
NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`, then restores
orders. This avoids dropping users and preserves every order and `user_id`.
`created_at` is copied from the existing rows, never regenerated.

## Dirty-data cleanup

Cleanup is deterministic by user id: `u4` becomes
`ada+u4@example.com`, `u5` becomes `missing+u5@example.invalid`, and `u6`
becomes `missing+u6@example.invalid`. The existing `ada@example.com` row is
not changed. The new NOT NULL and UNIQUE constraints reject invalid future
writes.

## Idempotency

The migration does not depend on a one-time marker. Each run copies the
current rows and replaces the tables with the same definitions. The cleanup
mapping is stable after the first run, so a second run neither duplicates nor
deletes data.

## Rollback

`rollback.sql` is executable after migration. It rebuilds `users` to the old
shape (`id`, `email`, `name`, `created_at`) while preserving the migrated
values, users, orders, and order references. It intentionally does not restore
the original dirty duplicate/NULL/blank values, because those values have been
cleaned and cannot be represented safely under the migrated constraints.

## Postcheck

Run `postcheck.sql` after migration. It checks user and order counts, grouped
order references and orphan orders, the three required cleaned emails, zero
NULL/blank or duplicate emails, zero NULL statuses, and the users table
metadata via `PRAGMA table_info` and `PRAGMA index_list`. It also compares the
dirty users' expected order ids and `user_id` values (`o2`/`u4`, `o3`/`u5`, and
`o4`/`u6`).
