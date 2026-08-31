-- Roll back the billing migration and restore the legacy table shapes.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE invoices_old (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO invoices_old(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at FROM invoices;

CREATE TABLE payments_old (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO payments_old(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments;
INSERT OR IGNORE INTO payments_old(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payment_orphans;

DROP TABLE payments;
DROP TABLE invoices;
ALTER TABLE invoices_old RENAME TO invoices;
ALTER TABLE payments_old RENAME TO payments;
DROP TABLE payment_orphans;

COMMIT;
PRAGMA foreign_keys = ON;
