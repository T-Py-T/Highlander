# Migration report

## Strategy

`migration.sql` runs in an explicit `BEGIN IMMEDIATE` transaction. It rebuilds
`users` because SQLite cannot add a UNIQUE constraint safely to the dirty
existing column in place. It also rebuilds `orders` in the same transaction,
copying every order before dropping the old tables. This preserves every
`orders.user_id` value and keeps foreign keys pointed at the new `users` table.
Historical `created_at` values are copied unchanged.

The new `users` table declares `email TEXT NOT NULL UNIQUE` and
`status TEXT NOT NULL DEFAULT 'active'`.

## Dirty-data cleanup

The duplicate `u4` email is changed from `ada@example.com` to
`ada+u4@example.com`; the first row, `u1`, keeps `ada@example.com`. The NULL
email for `u5` becomes `missing+u5@example.invalid`, and the blank email for
`u6` becomes `missing+u6@example.invalid`. These values are deterministic and
are documented in `preflight_report.md`.

## Idempotency

A metadata marker is created with `CREATE TABLE IF NOT EXISTS` and
`INSERT OR IGNORE`. The table rebuild itself copies the current tables on each
run, so a second execution neither inserts duplicate rows nor applies a
second conflicting cleanup. It remains enclosed in one transaction; a
failure rolls back the rebuild and leaves the prior schema/data intact.

## Rollback behavior and limitation

`rollback.sql` is intended to run after a successful migration. It rebuilds
both `orders` and `users` in a transaction, restores the old users shape
(`id`, `email`, `name`, `created_at`), and preserves row counts and order
references. It drops the migration marker. It cannot reconstruct the original
NULL, blank, or duplicate email values because those values were deliberately
normalized; it retains the migrated deterministic email values instead.

## Postcheck

Run `postcheck.sql` after migration. It checks six users, four orders, the
`o2`/`o3`/`o4` references to `u4`/`u5`/`u6`, the three deterministic cleaned
emails, non-null/nonblank/unique emails, active non-null statuses, and the
column/index declarations for the email and status constraints.
