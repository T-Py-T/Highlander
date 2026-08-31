-- Billing schema migration. Run as a single SQLite script.
-- foreign_keys must be disabled while the two parent/child tables are rebuilt;
-- it is restored before this script finishes.
PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- This ledger preserves status values across an idempotent table rebuild. It
-- is removed by rollback and is not part of the public billing schema.
CREATE TABLE IF NOT EXISTS _billing_invoice_status (
  invoice_id TEXT PRIMARY KEY,
  status TEXT NOT NULL
);
INSERT OR IGNORE INTO _billing_invoice_status(invoice_id, status)
SELECT id, 'open' FROM invoices;

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

DROP TABLE IF EXISTS invoices_new;
CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);
INSERT INTO invoices_new(id, customer_id, total_cents, created_at, status)
SELECT i.id, i.customer_id, i.total_cents, i.created_at,
       COALESCE(s.status, 'open')
FROM invoices AS i
LEFT JOIN _billing_invoice_status AS s ON s.invoice_id = i.id;
DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

DROP TABLE IF EXISTS payments_new;
CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO payments_new(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
JOIN invoices AS i ON i.id = p.invoice_id;
DROP TABLE payments;
ALTER TABLE payments_new RENAME TO payments;

COMMIT;
PRAGMA foreign_keys = ON;
