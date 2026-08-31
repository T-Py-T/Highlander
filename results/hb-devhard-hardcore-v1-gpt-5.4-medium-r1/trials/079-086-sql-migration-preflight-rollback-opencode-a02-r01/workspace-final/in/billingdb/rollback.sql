PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

DROP TABLE IF EXISTS invoices__rollback_old;
DROP TABLE IF EXISTS payments__rollback_old;

CREATE TABLE invoices__rollback_old (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices__rollback_old (id, customer_id, total_cents, created_at)
SELECT id,
       customer_id,
       total_cents,
       created_at
FROM invoices;

CREATE TABLE payments__rollback_old (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments__rollback_old (id, invoice_id, amount_cents, created_at)
SELECT id,
       invoice_id,
       amount_cents,
       created_at
FROM payments;

INSERT OR IGNORE INTO payments__rollback_old (id, invoice_id, amount_cents, created_at)
SELECT id,
       invoice_id,
       amount_cents,
       created_at
FROM payment_orphans;

DROP TABLE payments;
DROP TABLE invoices;

ALTER TABLE invoices__rollback_old RENAME TO invoices;
ALTER TABLE payments__rollback_old RENAME TO payments;

COMMIT;

PRAGMA foreign_keys = ON;
