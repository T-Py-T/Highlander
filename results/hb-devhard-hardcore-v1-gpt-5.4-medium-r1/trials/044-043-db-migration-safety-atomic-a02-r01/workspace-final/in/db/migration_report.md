# Migration report

## Strategy

- Run in one explicit transaction with `PRAGMA foreign_keys = OFF` during the table rebuild.
- Copy current `users` rows into a temp table.
- Recreate `users` with the target schema:
  - `status TEXT NOT NULL DEFAULT 'active'`
  - `email TEXT NOT NULL UNIQUE CHECK (length(trim(email)) > 0)`
- Reinsert all users with preserved `id`, `name`, and `created_at` values.
- Keep `orders` untouched so `orders.user_id` stays tied to the same user ids.

## Dirty-data cleanup

The migration keeps all users and rewrites only the unsafe email values.

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

The script also keeps a fallback cleanup rule for any later null or blank email rows: `missing+<id>@example.invalid`.

## Idempotency

The migration is safe to run twice.

- It always copies the current `users` table into a temp table first.
- It rebuilds `users` from that temp copy.
- It does not insert extra rows or change user ids.
- The fixed cleanup values for `u4`, `u5`, and `u6` stay the same on rerun.

## Rollback behavior and limit

Run `db/rollback.sql` after the migration to restore the old schema shape:

- `id`
- `email`
- `name`
- `created_at`

Rollback preserves user rows, order rows, user ids, and order references. It drops the `status` column and removes the new email constraints by rebuilding `users` in the old shape.

Limit: rollback restores the old schema shape, not the original dirty email values. Cleaned migrated email values stay in place.

## Postcheck queries

Run `db/postcheck.sql` after the migration. It checks:

- user and order row counts
- orders for `u4`, `u5`, and `u6`
- exact cleaned email values for dirty users
- absence of null, blank, and duplicate emails
- status population
- schema text for email and status constraints
- foreign key integrity with `PRAGMA foreign_key_check`
