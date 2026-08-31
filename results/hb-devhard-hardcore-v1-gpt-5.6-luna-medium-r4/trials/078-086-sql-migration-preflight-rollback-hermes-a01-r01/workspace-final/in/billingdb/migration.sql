-- Billing schema migration: add invoice status and enforce future payment references.
-- This script is safe to run repeatedly against the supplied old schema or the
-- already-migrated schema.  Foreign-key enforcement is enabled before the
-- transaction and remains enabled after it.
PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

-- Keep this table across reruns.  INSERT OR IGNORE makes orphan capture
-- idempotent by the payment id.
CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at,
       'invoice_id does not reference an existing invoice'
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

-- Stage payments without a foreign key while the parent table is rebuilt.
-- Only valid payments remain in the live payments table; captured orphans are
-- retained in payment_orphans.
DROP TABLE IF EXISTS payments_stage;
CREATE TABLE payments_stage (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO payments_stage(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
JOIN invoices AS i ON i.id = p.invoice_id;
DROP TABLE payments;

-- Rebuild invoices so this works on SQLite versions without DROP COLUMN.
-- The supplied source schema has no status column; reruns intentionally
-- reconstruct status as the declared default ('open').
DROP TABLE IF EXISTS invoices_stage;
CREATE TABLE invoices_stage (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);
INSERT INTO invoices_stage(id, customer_id, total_cents, created_at, status)
SELECT id, customer_id, total_cents, created_at, 'open'
FROM invoices;
DROP TABLE invoices;
ALTER TABLE invoices_stage RENAME TO invoices;

-- Install the enforced payments table after the parent is in its final shape.
CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO payments(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments_stage;
DROP TABLE payments_stage;

COMMIT;
PRAGMA foreign_keys = ON;
