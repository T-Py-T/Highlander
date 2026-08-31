# Migration Report

## Strategy

The migration runs in an explicit SQLite transaction. It copies users into a
new table with `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT
'active'`, then copies orders into a table referencing the new users table.
Orders are dropped only after their complete copy succeeds; both replacements
are then renamed atomically. Historical `created_at` values and all IDs are
copied unchanged.

## Dirty-data cleanup

The existing `ada@example.com` row for `u1` remains unchanged. The duplicate
`u4` becomes `ada+u4@example.com`; `u5`'s NULL becomes
`missing+u5@example.invalid`; and blank `u6` becomes
`missing+u6@example.invalid`. The `u4`, `u5`, and `u6` order references are not
changed.

## Idempotency

The script rebuilds from the current users and orders on each invocation,
always applying the same ID-based cleanup. Temporary tables are removed first,
so a second successful run neither duplicates nor loses rows.

## Rollback

Run `rollback.sql` after migration. It rebuilds users with the old columns
`id`, `email`, `name`, and `created_at`, while preserving users and orders.
Rollback intentionally retains the deterministic cleaned email values; the
original NULL, blank, and duplicate values cannot be reconstructed after
cleanup. The old shape permits nullable/non-unique emails again.

## Postcheck

Run `postcheck.sql` after migration. It checks user and order counts, dependent
orders for dirty users, exact cleaned emails, email/status column constraints,
and null/blank or duplicate email violations.
