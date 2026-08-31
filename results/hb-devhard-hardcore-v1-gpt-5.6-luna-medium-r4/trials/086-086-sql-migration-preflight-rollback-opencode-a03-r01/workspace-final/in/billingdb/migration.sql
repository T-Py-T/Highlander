-- Run this file as one unit.  The pragma is deliberately outside the
-- transaction because SQLite does not change it while a transaction is open.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

-- Archive before replacing payments.  The primary key and predicate make
-- this safe to execute again after a partially or fully completed migration.
INSERT INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at,
       'invoice_id does not reference an invoice at migration time'
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id)
  AND NOT EXISTS (SELECT 1 FROM payment_orphans AS o WHERE o.id = p.id);

DROP TABLE IF EXISTS payments_valid;
CREATE TABLE payments_valid (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO payments_valid(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
WHERE EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);
DROP TABLE payments;

DROP TABLE IF EXISTS invoices_new;
CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices_new(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

DROP TABLE IF EXISTS payments_new;
CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL REFERENCES invoices(id),
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

-- Only valid payments remain in the constrained table; archived payments are
-- retained verbatim in payment_orphans.
INSERT INTO payments_new(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments_valid;
DROP TABLE payments_valid;
ALTER TABLE payments_new RENAME TO payments;

COMMIT;
PRAGMA foreign_keys = ON;
