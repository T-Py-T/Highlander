# Migration report

## Strategy

The migration runs in one explicit `BEGIN IMMEDIATE` transaction. It creates a
new constrained `users` table, copies every user while preserving `id`, `name`,
and `created_at`, then copies `orders` to a dependent table that references the
new parent. Only after both copies succeed does it drop the old tables and
rename the replacements. This preserves every order and its `user_id`.

## Dirty-data cleanup

The duplicate `u4` email becomes `ada+u4@example.com`; the first
`ada@example.com` row (`u1`) stays unchanged. The null `u5` email becomes
`missing+u5@example.invalid`, and the blank `u6` email becomes
`missing+u6@example.invalid`. The new `email TEXT NOT NULL UNIQUE` definition
rejects null or duplicate future writes. `status` is `TEXT NOT NULL DEFAULT
'active'`.

## Idempotency

Temporary replacement tables are dropped if present, and each run rebuilds the
same tables from the current data with deterministic cleanup. A second run
therefore neither inserts duplicate rows nor leaves stale replacement tables.

## Rollback

`rollback.sql` uses the same dependent-first rebuild inside a transaction and
restores `users` to exactly `id`, `email`, `name`, `created_at`; it keeps order
rows and references. It cannot restore the original dirty email text because
the migration intentionally replaces those values, so rollback retains the
cleaned values and removes only the `status` column and its constraints.

## Postcheck

Run `postcheck.sql` after migration. It checks user/order counts, orphan orders,
orders for `u4`/`u5`/`u6`, exact cleaned emails, null/blank/duplicate email
counts, `users` column metadata (including email/status constraints and the
status default), unique indexes, and `PRAGMA foreign_key_check`.
