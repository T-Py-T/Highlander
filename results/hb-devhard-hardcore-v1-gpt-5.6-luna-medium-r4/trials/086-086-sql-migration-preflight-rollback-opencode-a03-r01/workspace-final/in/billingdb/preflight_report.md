# Billing Migration Preflight

Source: `schema.sql` and the data present before migration.

| Object | Rows |
| --- | ---: |
| `invoices` | 3 |
| `payments` | 4 |
| Payments with a valid invoice | 3 |
| Orphan payments | 1 |

The orphan is `p4`: invoice `missing-invoice`, amount `700`, created at
`2024-01-07T10:00:00Z`. It must be copied unchanged to `payment_orphans` with
the migration reason; it must not be deleted.

The migration must be run against a backup, as with any destructive SQLite
table rebuild. It enables foreign keys before beginning its explicit
transaction and leaves them enabled after commit.
