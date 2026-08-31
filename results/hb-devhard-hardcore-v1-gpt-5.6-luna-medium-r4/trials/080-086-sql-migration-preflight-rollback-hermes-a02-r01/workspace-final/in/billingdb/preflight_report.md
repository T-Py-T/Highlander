# Billing migration preflight report

## Scope

Input: `schema.sql`; migration target: `migration.sql`.

## Source inventory

The supplied seed schema contains:

- `invoices`: 3 rows (`inv1`, `inv2`, `inv3`)
- `payments`: 4 rows (`p1`, `p2`, `p3`, `p4`)
- orphan payments: 1 row, `p4`, referencing `missing-invoice`

The three invoice timestamps are historical data and must be copied unchanged.

## Planned safety checks

Before enforcing the payment foreign key, the migration copies every payment whose
`invoice_id` is absent from `invoices` into `payment_orphans`, preserving `id`,
`invoice_id`, `amount_cents`, and `created_at`, with a reason. It then rebuilds
`payments` with a foreign key to `invoices(id)` and copies only valid payments.

Invoices are rebuilt with `status TEXT NOT NULL DEFAULT 'open'`; all legacy invoice
columns, including `created_at`, are copied. A durable status map makes rerunning
the migration idempotent without duplicating rows or resetting assigned statuses.

Expected post-migration counts:

- `invoices`: 3
- `payments`: 3
- `payment_orphans`: 1 (`p4`)
- `invoices.status IS NULL`: 0
- foreign-key violations: 0

The migration uses `BEGIN IMMEDIATE`/`COMMIT`, and leaves `PRAGMA foreign_keys`
enabled. See `postcheck.sql` for executable checks.
