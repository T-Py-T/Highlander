PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

DROP TABLE IF EXISTS payments__rollback;
CREATE TABLE payments__rollback (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments__rollback (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments;

INSERT OR IGNORE INTO payments__rollback (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payment_orphans;

DROP TABLE payments;
DROP INDEX IF EXISTS idx_payments_invoice_id;

DROP TABLE IF EXISTS invoices__rollback;
CREATE TABLE invoices__rollback (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices__rollback (id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices__rollback RENAME TO invoices;
ALTER TABLE payments__rollback RENAME TO payments;
DROP TABLE IF EXISTS payment_orphans;

COMMIT;
PRAGMA foreign_keys = ON;
