# Migration Report

## Strategy

The migration uses an explicit `BEGIN IMMEDIATE ... COMMIT` transaction and rebuilds both `users` and `orders` offline with foreign keys temporarily disabled during the table swap. This avoids in-place destructive edits, preserves every user id, keeps every `orders.user_id` reference intact, and retains historical `created_at` values.

To support rollback, the script creates `users__migration_backup` once and stores the exact pre-migration `users` rows there before any schema change. That backup is not overwritten on later runs.

## Dirty-data cleanup

The migration applies the required deterministic email repairs while copying users into the new constrained table:

| User id | Legacy problem | Migrated email |
| --- | --- | --- |
| `u4` | duplicate `ada@example.com` | `ada+u4@example.com` |
| `u5` | `NULL` email | `missing+u5@example.invalid` |
| `u6` | blank email | `missing+u6@example.invalid` |

User `u1` remains the canonical owner of `ada@example.com`.

## Idempotency behavior

The migration is safe to rerun against the migrated database without duplicating rows:

- `users__migration_backup` is populated with `INSERT OR IGNORE`, so the original snapshot is kept once.
- Replacement working tables are dropped and recreated on each run.
- Users are recopied by stable primary key, so the result remains one row per user id.
- Orders are recopied with the same primary keys and `user_id` references.

Because the migration always rewrites the constrained `users` table from the current table contents, rerunning it immediately after a successful migration is a no-op at the data level.

## Rollback behavior and limitation

Run `sqlite3 <dbfile> < in/db/rollback.sql` after the migration to restore the legacy `users` schema shape:

- Restored columns: `id`, `email`, `name`, `created_at`
- Preserved rows: all users and all orders
- Preserved dirty legacy values: yes, via `users__migration_backup`

The rollback only restores the `users` schema shape and data payload. It intentionally leaves the backup table in place so the historical pre-migration snapshot remains available.

## Postcheck queries

Run `sqlite3 <dbfile> < in/db/postcheck.sql` after the migration. The postcheck verifies:

- user and order row counts
- preserved dependent orders for `u4`, `u5`, and `u6`
- deterministic cleaned emails for dirty users
- absence of null, blank, and duplicate emails
- presence of `status` constraints and foreign-key consistency
