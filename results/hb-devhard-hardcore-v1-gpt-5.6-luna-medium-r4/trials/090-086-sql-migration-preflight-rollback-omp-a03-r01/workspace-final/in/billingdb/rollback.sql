-- Restore the pre-migration invoices and payments shapes.
-- Keep foreign-key enforcement disabled only for the table swap, then restore it.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

DROP TABLE IF EXISTS payments_old;
CREATE TABLE payments_old (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO payments_old(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments;
-- Put preserved historical orphans back into the legacy payments table.
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
INSERT OR IGNORE INTO invoices_old(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at FROM invoices;
DROP TABLE invoices;
ALTER TABLE invoices_old RENAME TO invoices;

COMMIT;
PRAGMA foreign_keys = ON;
