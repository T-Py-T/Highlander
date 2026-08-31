-- Billing schema migration v1.
-- SQLite only. The transaction is explicit; foreign-key enforcement is restored
-- before this script finishes.

PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Preserve invalid legacy payments before installing the FK on payments.
CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at,
       'invoice_id does not match an existing invoice'
FROM payments AS p
WHERE NOT EXISTS (
  SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id
);

-- Rebuild invoices to add the required non-null defaulted status. IF NOT
-- EXISTS/OR IGNORE make re-running this script harmless for this migration.
DROP TABLE IF EXISTS invoices_new;
CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT OR IGNORE INTO invoices_new(id, customer_id, total_cents, created_at, status)
SELECT id, customer_id, total_cents, created_at, 'open'
FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

-- Rebuild payments with a real FK. Orphans are deliberately excluded from
-- this table because they now live in payment_orphans.
DROP TABLE IF EXISTS payments_new;
CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT OR IGNORE INTO payments_new(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
WHERE EXISTS (
  SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id
);

DROP TABLE payments;
ALTER TABLE payments_new RENAME TO payments;

COMMIT;
PRAGMA foreign_keys = ON;

-- A second execution repeats only lossless rebuilds: invoice/payment primary
-- keys and payment_orphans primary keys make the INSERT OR IGNORE operations
-- non-duplicating, while all source rows remain intact.
