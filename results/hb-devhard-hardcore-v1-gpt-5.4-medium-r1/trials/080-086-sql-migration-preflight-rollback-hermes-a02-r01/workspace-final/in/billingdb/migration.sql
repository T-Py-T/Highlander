PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans (id, invoice_id, amount_cents, created_at, reason)
SELECT p.id,
       p.invoice_id,
       p.amount_cents,
       p.created_at,
       'missing_invoice_reference'
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices_new (id, customer_id, total_cents, created_at)
SELECT id,
       customer_id,
       total_cents,
       created_at
FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT INTO payments_new (id, invoice_id, amount_cents, created_at)
SELECT p.id,
       p.invoice_id,
       p.amount_cents,
       p.created_at
FROM payments AS p
INNER JOIN invoices AS i ON i.id = p.invoice_id;

DROP TABLE payments;
ALTER TABLE payments_new RENAME TO payments;
CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);

COMMIT;
PRAGMA foreign_keys = ON;
