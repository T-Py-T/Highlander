# Billing migration preflight

Source: `schema.sql`.

| Check | Result |
|---|---:|
| Invoices | 3 |
| Payments | 4 |
| Payments referencing an existing invoice | 3 |
| Orphan payments | 1 |
| Orphan payment IDs | `p4` |

`p4` references `missing-invoice`, has amount `700`, and was created at
`2024-01-07T10:00:00Z`. The migration must copy this row to
`payment_orphans` before replacing `payments`; it must not delete the row.

The source invoices have no `status` column. The migration adds it as
`TEXT NOT NULL DEFAULT 'open'` while copying the existing invoice identity,
amount, and historical `created_at` values unchanged.
