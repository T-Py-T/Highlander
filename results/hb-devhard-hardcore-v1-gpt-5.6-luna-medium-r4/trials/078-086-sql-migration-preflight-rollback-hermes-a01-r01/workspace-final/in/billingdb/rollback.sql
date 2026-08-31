-- Restore the original invoices/payments column shapes.
-- payment_orphans is retained as an audit/preservation table.
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

DROP TABLE IF EXISTS payments_rollback;
CREATE TABLE payments_rollback (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO payments_rollback(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments;
INSERT OR IGNORE INTO payments_rollback(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payment_orphans;
DROP TABLE payments;
ALTER TABLE payments_rollback RENAME TO payments;

DROP TABLE IF EXISTS invoices_rollback;
CREATE TABLE invoices_rollback (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO invoices_rollback(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at FROM invoices;
DROP TABLE invoices;
ALTER TABLE invoices_rollback RENAME TO invoices;

COMMIT;
PRAGMA foreign_keys = ON;
