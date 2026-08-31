PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id,
       p.invoice_id,
       p.amount_cents,
       p.created_at,
       'missing invoice during migration'
FROM payments AS p
LEFT JOIN invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

DROP TABLE IF EXISTS invoices__migration_new;

CREATE TABLE invoices__migration_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices__migration_new(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices__migration_new RENAME TO invoices;

DROP TABLE IF EXISTS payments__migration_new;

CREATE TABLE payments__migration_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT INTO payments__migration_new(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
INNER JOIN invoices AS i
  ON i.id = p.invoice_id;

DROP TABLE payments;
ALTER TABLE payments__migration_new RENAME TO payments;

COMMIT;

PRAGMA foreign_keys = ON;
