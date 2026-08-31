-- Restore the pre-migration table shapes and put archived payments back.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

DROP TABLE IF EXISTS payments_old;
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

DROP TABLE IF EXISTS invoices_old;
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

DROP TABLE IF EXISTS payment_orphans;

COMMIT;
PRAGMA foreign_keys = ON;
