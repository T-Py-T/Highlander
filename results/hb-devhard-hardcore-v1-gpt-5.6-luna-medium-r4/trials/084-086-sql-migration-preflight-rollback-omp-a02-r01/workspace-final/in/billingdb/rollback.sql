-- Restore the legacy billing schema and put quarantined payments back.
-- foreign_keys must be off while the FK-bearing table is replaced; it is
-- explicitly restored before this script completes.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

ALTER TABLE payments RENAME TO payments_migrated;
ALTER TABLE invoices RENAME TO invoices_migrated;

CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO invoices (id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices_migrated;
DROP TABLE invoices_migrated;
DROP TABLE invoice_status_backup;

CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments_migrated;
INSERT OR IGNORE INTO payments (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payment_orphans;
DROP TABLE payments_migrated;
DROP TABLE payment_orphans;

COMMIT;
PRAGMA foreign_keys = ON;
