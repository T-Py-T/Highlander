# Billing migration report

## Safety and behavior

- `migration.sql` uses `BEGIN IMMEDIATE` and commits all table changes as one
  transaction.
- Foreign-key enforcement is disabled only for the table rebuild, then
  explicitly restored with `PRAGMA foreign_keys = ON`.
- Existing orphan payments are copied to `payment_orphans` with the original
  four columns and reason `invoice does not exist`; valid payments are copied
  into the new foreign-key-protected `payments` table.
- Existing invoice rows and their original `created_at` values are copied
  unchanged. New invoices receive `status = 'open'` through the declared
  non-null default.
- `invoice_status_state` and its update trigger retain statuses across a
  rerun, so the migration does not reset caller-updated statuses. The state
  table is internal and is removed by `rollback.sql`.
- `INSERT OR IGNORE` for orphan/state bookkeeping and replacement-table
  construction make a completed second run non-duplicating. Orphans remain
  outside `payments` because they cannot satisfy the new foreign key.

## Rollback

`rollback.sql` rebuilds both tables to the original definitions, restores all
valid payments plus preserved orphan rows to `payments`, removes migration
bookkeeping, and restores foreign-key enforcement. It does not delete the
historical orphan; it changes its location back to the legacy table because
the old schema has no `payment_orphans` table.

## Postcheck

Run `postcheck.sql` after migration. It checks invoice/payment/orphan counts,
exact preservation of `p4`, status non-null/open defaults, invalid payment
references, actual foreign-key violations, and the `payments.invoice_id`
foreign-key definition.
