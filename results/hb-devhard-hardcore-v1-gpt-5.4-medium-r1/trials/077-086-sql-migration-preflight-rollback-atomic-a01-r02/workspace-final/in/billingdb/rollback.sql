PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS payments__rollback_new;
CREATE TABLE payments__rollback_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT OR REPLACE INTO payments__rollback_new (
  id,
  invoice_id,
  amount_cents,
  created_at
)
SELECT id,
       invoice_id,
       amount_cents,
       created_at
FROM payments;

INSERT OR REPLACE INTO payments__rollback_new (
  id,
  invoice_id,
  amount_cents,
  created_at
)
SELECT id,
       invoice_id,
       amount_cents,
       created_at
FROM payment_orphans;

DROP TABLE IF EXISTS invoices__rollback_new;
CREATE TABLE invoices__rollback_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT OR REPLACE INTO invoices__rollback_new (
  id,
  customer_id,
  total_cents,
  created_at
)
SELECT id,
       customer_id,
       total_cents,
       created_at
FROM invoices;

DROP TABLE payments;
ALTER TABLE payments__rollback_new RENAME TO payments;

DROP TABLE invoices;
ALTER TABLE invoices__rollback_new RENAME TO invoices;

DROP TABLE IF EXISTS payment_orphans;

COMMIT;

PRAGMA foreign_keys = ON;
