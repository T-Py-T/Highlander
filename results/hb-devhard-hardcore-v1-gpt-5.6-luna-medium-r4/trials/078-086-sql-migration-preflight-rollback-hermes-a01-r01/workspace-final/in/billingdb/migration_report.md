# Billing migration report

## Resulting schema

- `invoices` is rebuilt with columns `id`, `customer_id`, `total_cents`, `created_at`, and `status TEXT NOT NULL DEFAULT 'open'`.
- `payments` is rebuilt with its original four columns and `FOREIGN KEY (invoice_id) REFERENCES invoices(id)`.
- `payment_orphans` retains orphan payment rows with columns `id`, `invoice_id`, `amount_cents`, `created_at`, and `reason`.

## Data guarantees

- Invoice rows and historical `created_at` values are copied rather than regenerated.
- Valid payments are copied unchanged.
- Existing orphan payments are transferred to `payment_orphans`; `p4` is retained and is never deleted.
- Future invalid payment references fail under the foreign key.

## Operational guarantees

The migration is an explicit transaction (`BEGIN IMMEDIATE` through `COMMIT`). It stages replacement tables before swapping them, enables foreign-key enforcement before starting, and explicitly leaves it enabled afterward. The orphan table is persistent and orphan insertion is idempotent; staging tables are recreated on each run, so a second completed migration does not duplicate data.

`rollback.sql` is also transactional. It restores the old column shapes for `invoices` and `payments`, copies preserved orphan rows back into the old unconstrained `payments` table without deleting `payment_orphans`, and restores foreign-key enforcement at the end.

Run `postcheck.sql` after migration. Its failure queries return zero rows on success; its final queries provide counts, invoice statuses, FK state, and FK violations for auditability.
