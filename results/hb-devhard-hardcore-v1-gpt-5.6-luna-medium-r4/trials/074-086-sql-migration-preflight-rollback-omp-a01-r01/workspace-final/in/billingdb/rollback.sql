-- Roll back billing migration v1. Run as a standalone SQLite script.
-- Foreign keys are disabled only while tables are rebuilt, then restored.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE payments_old (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO payments_old(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments;
INSERT OR IGNORE INTO payments_old(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payment_orphans;
DROP TABLE payments;
ALTER TABLE payments_old RENAME TO payments;

CREATE TABLE invoices_old (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO invoices_old(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at FROM invoices;
DROP TABLE invoices;
ALTER TABLE invoices_old RENAME TO invoices;

DROP TRIGGER IF EXISTS invoices_status_state_sync;
DROP TABLE IF EXISTS invoice_status_state;
DROP TABLE IF EXISTS payment_orphans;

COMMIT;
PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;
