# Billing migration preflight report

## Source fixture
- `schema.sql` defines 3 invoices: `inv1`, `inv2`, `inv3`.
- `schema.sql` defines 4 payments: `p1`, `p2`, `p3`, `p4`.
- `seed_notes.md` marks `p4` as a real historical orphan that must be preserved.

## Pre-migration findings
- Invoice rows: 3
- Payment rows: 4
- Orphan payments: 1
- Orphan payment ids: `p4`
- Invoice timestamps to preserve:
  - `inv1`: `2024-01-03T10:00:00Z`
  - `inv2`: `2024-01-04T10:00:00Z`
  - `inv3`: `2024-01-05T10:00:00Z`

## Migration requirements applied
- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Preserve all invoice rows and historical `created_at` values.
- Preserve orphan payments by copying them into `payment_orphans` before referential enforcement.
- Rebuild `payments` with a foreign key so future `invoice_id` values must reference existing invoices.
- Run the migration inside an explicit transaction.
- Keep the migration idempotent for repeated execution against an already migrated database.

## Expected post-migration state
- `invoices`: 3 rows, all with `status = 'open'`.
- `payments`: 3 valid rows (`p1`, `p2`, `p3`).
- `payment_orphans`: 1 preserved row (`p4`).
- `PRAGMA foreign_key_check`: no violations.
