# Migration report

## Strategy

- Run offline in SQLite inside an explicit `BEGIN IMMEDIATE` transaction.
- Temporarily disable foreign-key enforcement during the table rebuild, then restore it and run `PRAGMA foreign_key_check`.
- Rebuild `users` instead of dropping data in place.
- Preserve every user id, every order row, every `orders.user_id` reference, and every historical `created_at` value.

## Dirty-data cleanup

The migration rewrites only the known dirty emails from the preflight dataset:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

`u1` remains the canonical `ada@example.com` row. All other user emails are copied through unchanged.

## Target constraints

The rebuilt `users` table enforces:

- `status TEXT NOT NULL DEFAULT 'active'`
- `email TEXT NOT NULL UNIQUE`
- `CHECK (LENGTH(TRIM(email)) > 0)` to reject blank future writes in addition to nulls and duplicates

## Idempotency approach

The migration is deterministic. Re-running it rebuilds `users` from the current table contents, reapplies the same cleanup mapping for `u4`, `u5`, and `u6`, and preserves ids, orders, and `created_at` values without duplicating rows.

## Rollback behavior and limitation

- `rollback.sql` rebuilds `users` back to the old schema shape: `id`, `email`, `name`, `created_at`.
- It preserves user-row count, order-row count, order references, and current email values.
- Limitation: rollback removes the `status` column and relaxed constraints, but it does not recover the original dirty emails once cleanup has been applied.

## Postcheck queries to run

Execute:

```sql
.read in/db/postcheck.sql
```

The postcheck verifies:

- user and order row counts
- preserved dirty-user order references (`u4`, `u5`, `u6`)
- exact cleaned email values for `u4`, `u5`, `u6`
- non-null, non-blank, unique email outcomes
- `status` column metadata and default
- unique-email index presence
- foreign-key integrity