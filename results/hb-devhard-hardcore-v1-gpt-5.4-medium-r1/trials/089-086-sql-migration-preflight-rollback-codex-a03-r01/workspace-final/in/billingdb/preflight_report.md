# Billing Migration Preflight Report

## Source schema summary

- `invoices` rows: 3
- `payments` rows: 4
- Expected invoice ids: `inv1`, `inv2`, `inv3`

## Orphan payment detection

One payment is orphaned in the source data because its `invoice_id` does not match any row in `invoices`.

| payment_id | invoice_id        | amount_cents | created_at            |
| ---------- | ----------------- | ------------ | --------------------- |
| `p4`       | `missing-invoice` | `700`        | `2024-01-07T10:00:00Z` |

## Migration requirements covered

- Preserve all invoice rows and historical `created_at` values.
- Add `invoices.status TEXT NOT NULL DEFAULT 'open'`.
- Preserve orphan payments by moving them into `payment_orphans` before enforcing referential integrity on `payments`.
- Rebuild `payments` with a foreign key to `invoices(id)`.
- Execute the migration inside an explicit transaction.
- Allow a second execution without duplicating invoices, payments, or orphan rows.
