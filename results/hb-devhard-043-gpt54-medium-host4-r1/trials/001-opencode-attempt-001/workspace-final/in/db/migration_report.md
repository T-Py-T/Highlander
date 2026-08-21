# Migration Report

## Strategy

The migration rebuilds both `users` and `orders` inside a single explicit transaction. It first copies current rows into temporary source tables, then recreates `users` with the target constraints and recreates `orders` so its foreign key points back to the rebuilt `users` table.

This avoids the unsafe draft behavior that dropped `users` in place and would have destroyed both user rows and dependent order references.

## Dirty-Data Cleanup

The migration preserves every existing user id and `created_at` value. It rewrites only the known dirty email rows using the required deterministic values:

- `u4` -> `ada+u4@example.com`
- `u5` -> `missing+u5@example.invalid`
- `u6` -> `missing+u6@example.invalid`

All other users keep their existing email values, with `u1` remaining the canonical `ada@example.com` row.

## Idempotency Approach

The script is safe to run twice because it always:

- copies the current `users` and `orders` rows into temporary tables,
- rebuilds the target tables from those copies,
- reapplies the same deterministic cleanup for `u4`, `u5`, and `u6`, and
- reinserts orders against the same preserved user ids.

Running the migration again does not duplicate rows or remap order ownership.

## Rollback Behavior And Limitation

`rollback.sql` restores the pre-migration `users` schema shape to `id`, `email`, `name`, and `created_at`, and it rebuilds `orders` so the foreign key still points at the restored `users` table.

Rollback preserves user and order row counts plus all order-to-user references, but it does not recover the original dirty email values. After migration, the deterministic cleaned email values remain in place because the rollback only restores the old schema shape, not the pre-cleanup data content.

## Postcheck Queries To Run

Run the verification script after migration:

```sql
.read in/db/postcheck.sql
```

The postcheck covers:

- user and order row counts,
- preserved dependent orders for `u4`, `u5`, and `u6`,
- required cleaned email values for those users,
- absence of null, blank, and duplicate emails,
- absence of null or blank statuses, and
- presence of the `users.status` definition and the email constraints in the rebuilt `users` table.
