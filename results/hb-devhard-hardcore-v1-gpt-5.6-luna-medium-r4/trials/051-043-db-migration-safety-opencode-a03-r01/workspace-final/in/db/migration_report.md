# Migration Report

## Strategy

`migration.sql` runs in an explicit `BEGIN IMMEDIATE` transaction. It creates
constrained replacement tables, copies users and orders, then swaps the tables
only after both copies succeed. IDs, order `user_id` values, and historical
`created_at` values are copied unchanged. Foreign keys are disabled only for
the table swap and re-enabled after commit.

## Dirty-data cleanup

The existing `ada@example.com` row is retained. `u4` is changed to
`ada+u4@example.com`; `u5` is changed to
`missing+u5@example.invalid`; and `u6` is changed to
`missing+u6@example.invalid`. The replacement `users` table makes email
non-null and unique and gives every user `status = 'active'`.

## Idempotency

Running the migration again rebuilds the tables without duplicating rows.
Each cleanup rule matches only its original dirty value, so already-cleaned
values remain unchanged. The unique and non-null constraints reject invalid
future writes.

## Rollback behavior

`rollback.sql` is executable after the migration. It preserves all users and
orders while restoring the legacy `users` column shape: `id`, `email`, `name`,
and `created_at`. It intentionally cannot restore the original duplicate,
NULL, or blank email values because that information is not safely reversible;
the cleanup values remain in the restored legacy-shaped table.

## Postcheck

Run `postcheck.sql` after migration. It reports user and order counts, checks
for orphan orders, lists orders for `u4`, `u5`, and `u6`, verifies the three
cleaned emails, checks null/blank/duplicate emails and invalid statuses, and
prints relevant table and index metadata for constraint inspection.
