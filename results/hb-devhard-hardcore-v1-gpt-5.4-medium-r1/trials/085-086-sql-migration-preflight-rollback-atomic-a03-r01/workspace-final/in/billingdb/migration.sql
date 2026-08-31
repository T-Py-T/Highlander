-- Billing migration: add invoices.status, preserve orphan payments, and enforce
-- future payment references through a foreign key.
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS invoices__new;
DROP TABLE IF EXISTS invoices__old;
DROP TABLE IF EXISTS payments__new;
DROP TABLE IF EXISTS payments__old;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans (
  id,
  invoice_id,
  amount_cents,
  created_at,
  reason
)
SELECT
  p.id,
  p.invoice_id,
  p.amount_cents,
  p.created_at,
  'missing invoice during billing migration'
FROM payments AS p
LEFT JOIN invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

DELETE FROM payments
WHERE id IN (
  SELECT id
  FROM payment_orphans
);

CREATE TABLE invoices__new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices__new (
  id,
  customer_id,
  total_cents,
  created_at,
  status
)
SELECT
  id,
  customer_id,
  total_cents,
  created_at,
  'open'
FROM invoices;

ALTER TABLE invoices RENAME TO invoices__old;
ALTER TABLE invoices__new RENAME TO invoices;

CREATE TABLE payments__new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT INTO payments__new (
  id,
  invoice_id,
  amount_cents,
  created_at
)
SELECT
  p.id,
  p.invoice_id,
  p.amount_cents,
  p.created_at
FROM payments AS p
INNER JOIN invoices AS i
  ON i.id = p.invoice_id;

ALTER TABLE payments RENAME TO payments__old;
ALTER TABLE payments__new RENAME TO payments;

DROP TABLE payments__old;
DROP TABLE invoices__old;

COMMIT;

PRAGMA foreign_keys = ON;
