-- Billing schema migration
-- Goals:
--   * add invoices.status TEXT NOT NULL DEFAULT 'open'
--   * preserve invoice created_at values
--   * preserve orphan payments in payment_orphans
--   * enforce valid payments.invoice_id references going forward
--   * remain safe to run more than once

PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

-- Capture any currently orphaned payments exactly once before rebuilding tables.
INSERT INTO payment_orphans (id, invoice_id, amount_cents, created_at, reason)
SELECT p.id,
       p.invoice_id,
       p.amount_cents,
       p.created_at,
       'missing invoice during billing migration'
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL
  AND NOT EXISTS (
    SELECT 1
    FROM payment_orphans AS po
    WHERE po.id = p.id
  );

-- Remove migrated orphans from payments so referential integrity can be enforced.
DELETE FROM payments
WHERE id IN (
  SELECT po.id
  FROM payment_orphans AS po
);

-- Rebuild invoices into the target shape every run so the script is idempotent.
DROP TABLE IF EXISTS invoices__migration_new;
CREATE TABLE invoices__migration_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices__migration_new (id, customer_id, total_cents, created_at, status)
SELECT id,
       customer_id,
       total_cents,
       created_at,
       'open'
FROM invoices;

DROP TABLE invoices;
ALTER TABLE invoices__migration_new RENAME TO invoices;

-- Rebuild payments with a foreign key now that only valid rows remain.
DROP TABLE IF EXISTS payments__migration_new;
CREATE TABLE payments__migration_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT INTO payments__migration_new (id, invoice_id, amount_cents, created_at)
SELECT p.id,
       p.invoice_id,
       p.amount_cents,
       p.created_at
FROM payments AS p
JOIN invoices AS i ON i.id = p.invoice_id;

DROP TABLE payments;
ALTER TABLE payments__migration_new RENAME TO payments;

CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payment_orphans_invoice_id ON payment_orphans(invoice_id);

COMMIT;

PRAGMA foreign_keys = ON;
