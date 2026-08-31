-- Roll back the billing migration to the original table shapes.
-- Restores:
--   invoices(id, customer_id, total_cents, created_at)
--   payments(id, invoice_id, amount_cents, created_at)
-- Historical orphan payments are merged back into payments.

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TABLE IF EXISTS payments__rollback_old;
CREATE TABLE payments__rollback_old (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments__rollback_old (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments;

INSERT INTO payments__rollback_old (id, invoice_id, amount_cents, created_at)
SELECT po.id, po.invoice_id, po.amount_cents, po.created_at
FROM payment_orphans AS po
WHERE NOT EXISTS (
  SELECT 1 FROM payments__rollback_old AS p WHERE p.id = po.id
);

DROP TABLE payments;
ALTER TABLE payments__rollback_old RENAME TO payments;
DROP INDEX IF EXISTS idx_payments_invoice_id;

DROP TABLE IF EXISTS invoices__rollback_old;
CREATE TABLE invoices__rollback_old (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices__rollback_old (id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices__rollback_old RENAME TO invoices;

DROP INDEX IF EXISTS idx_payment_orphans_invoice_id;
DROP TABLE IF EXISTS payment_orphans;

COMMIT;

PRAGMA foreign_keys = ON;
