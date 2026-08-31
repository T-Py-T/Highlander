PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

DROP TABLE IF EXISTS invoices__rollback_new;
DROP TABLE IF EXISTS payments__rollback_new;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE invoices__rollback_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO invoices__rollback_new(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices;

CREATE TABLE payments__rollback_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO payments__rollback_new(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments;

INSERT OR IGNORE INTO payments__rollback_new(id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payment_orphans;

DROP TABLE payments;
DROP TABLE invoices;

ALTER TABLE invoices__rollback_new RENAME TO invoices;
ALTER TABLE payments__rollback_new RENAME TO payments;

DROP TABLE IF EXISTS payment_orphans;

COMMIT;
PRAGMA foreign_keys = OFF;
