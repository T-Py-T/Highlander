-- Roll back the billing migration to the old table shape.
PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS invoices__rollback;
DROP TABLE IF EXISTS invoices__old;
DROP TABLE IF EXISTS payments__rollback;
DROP TABLE IF EXISTS payments__old;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE invoices__rollback (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices__rollback (
  id,
  customer_id,
  total_cents,
  created_at
)
SELECT
  id,
  customer_id,
  total_cents,
  created_at
FROM invoices;

CREATE TABLE payments__rollback (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments__rollback (
  id,
  invoice_id,
  amount_cents,
  created_at
)
SELECT
  id,
  invoice_id,
  amount_cents,
  created_at
FROM payments;

INSERT OR IGNORE INTO payments__rollback (
  id,
  invoice_id,
  amount_cents,
  created_at
)
SELECT
  id,
  invoice_id,
  amount_cents,
  created_at
FROM payment_orphans;

ALTER TABLE invoices RENAME TO invoices__old;
ALTER TABLE invoices__rollback RENAME TO invoices;
DROP TABLE invoices__old;

ALTER TABLE payments RENAME TO payments__old;
ALTER TABLE payments__rollback RENAME TO payments;
DROP TABLE payments__old;

DROP TABLE IF EXISTS payment_orphans;

COMMIT;

PRAGMA foreign_keys = ON;
