# Migration Report

## Strategy

The migration replaces the destructive draft with a transactional copy-and-swap:

1. Disable foreign key enforcement for the table rebuild.
2. Start an explicit `BEGIN IMMEDIATE` transaction.
3. Persist source rows into `users__migration_state`.
4. Apply deterministic email cleanup inside that state table.
5. Build a new constrained `users` table with `email TEXT NOT NULL UNIQUE` and `status TEXT NOT NULL DEFAULT 'active'`.
6. Copy all users into the new table while preserving `id`, `name`, and historical `created_at`.
7. Swap the new table into place and commit.

Because `orders.user_id` continues to reference the same user ids, dependent orders remain attached to the same users after the swap.

## Dirty-Data Cleanup

Required fixes applied by the migration:

- Keep `u1` as `ada@example.com`.
- Rewrite duplicate user `u4` to `ada+u4@example.com`.
- Rewrite null-email user `u5` to `missing+u5@example.invalid`.
- Rewrite blank-email user `u6` to `missing+u6@example.invalid`.

These values are deterministic and preserve all legacy users instead of dropping them.

## Idempotency

`users__migration_state` is intentionally kept as the canonical migration staging table. The script seeds it with `INSERT OR IGNORE`, so rerunning the migration does not duplicate users or produce new cleanup variants. A second run rebuilds `users` from the same staged row set, preserving user ids, cleaned emails, and `created_at` values.

## Rollback Behavior

`rollback.sql` rebuilds `users` back to the pre-migration shape:

- `id`
- `email`
- `name`
- `created_at`

Rollback preserves the same user-row count and order-row count. It does not restore the original dirty email values; it preserves the migrated email values while removing the `status` column and the new email constraints.

## Postcheck Queries

Run:

```sql
.read /workspace/in/db/postcheck.sql
```

The postcheck verifies:

- user and order row counts
- continued presence of dependent orders for `u4`, `u5`, and `u6`
- deterministic cleaned email values for dirty users
- absence of null, blank, or duplicate emails
- schema-level `NOT NULL`, `UNIQUE`, and `status` definitions on `users`
