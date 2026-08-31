# Migration report

## Strategy

The migration rebuilds `users` inside an explicit `BEGIN IMMEDIATE` transaction instead of altering rows in place or dropping data. It temporarily disables SQLite foreign-key enforcement during the table swap so the existing `orders.user_id` references survive the `DROP TABLE users` / rename sequence, then restores foreign-key enforcement after commit.

The new `users` table shape is:

- `id TEXT PRIMARY KEY`
- `email TEXT NOT NULL UNIQUE CHECK (length(trim(email)) > 0)`
- `name TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'active'`
- `created_at TEXT NOT NULL`

This preserves all user ids, preserves historical `created_at` values, adds non-null `status` with default `active`, and enforces unique non-null non-blank emails for future writes.

## Dirty-data cleanup

Before adding constraints, the migration deterministically rewrites only the known dirty rows:

- `u4`: `ada@example.com` -> `ada+u4@example.com`
- `u5`: `NULL` -> `missing+u5@example.invalid`
- `u6`: `''` -> `missing+u6@example.invalid`

The original valid `ada@example.com` row for `u1` is preserved unchanged.

## Idempotency approach

The migration is safe to run more than once because it always rebuilds `users` into the same target schema and applies the same deterministic cleanup mapping keyed by user id. Re-running it does not create duplicate rows, change user ids, alter `created_at`, or duplicate orders. The script writes `status = 'active'` for every migrated row, so a second run over the just-migrated dataset is a no-op for status values as well.

## Rollback behavior and limitation

`rollback.sql` rebuilds `users` back to the pre-migration schema shape:

- `id`
- `email`
- `name`
- `created_at`

It preserves the same number of user rows and order rows, and keeps order references on the same user ids.

Limitation: rollback restores the old schema shape, but not the original dirty email values. The cleaned email values remain, because the migration does not keep a separate historical backup table.

## Postcheck queries to run

After applying the migration, execute `postcheck.sql`. It verifies:

1. User row count is still 6.
2. Order row count is still 4.
3. Dirty-user dependent orders for `u4`, `u5`, and `u6` still exist.
4. Dirty-user emails were rewritten to the required deterministic values.
5. Historical `created_at` values for legacy dirty users were preserved.
6. The `users` schema now includes `status`, and `email` is constrained through table/index metadata.
7. No rows remain with null/blank emails, no duplicate email groups remain, and no rows have null status.
