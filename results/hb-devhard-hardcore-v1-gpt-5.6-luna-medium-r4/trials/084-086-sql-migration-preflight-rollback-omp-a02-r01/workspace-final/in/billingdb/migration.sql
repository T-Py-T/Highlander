-- Billing schema upgrade.
-- The script rebuilds both tables so it is repeatable on either the legacy
-- schema or the already-migrated schema. All data-changing DDL is transactional.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- Keep the source payments available while invoices and the FK are rebuilt.
DROP TABLE IF EXISTS payments_old;
DROP TRIGGER IF EXISTS invoices_status_backup_sync;
ALTER TABLE payments RENAME TO payments_old;

-- Quarantine invalid historical payments before enforcing the new FK.
CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);
INSERT OR IGNORE INTO payment_orphans (id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at,
       'invoice_id did not match an invoice during migration'
FROM payments_old AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;
 
-- Keep status values across repeat executions without referring to a
-- non-existent legacy column on the first execution.
CREATE TABLE IF NOT EXISTS invoice_status_backup (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL
);

-- Rebuild invoices with the new required column. Existing invoice fields,
-- including historical created_at values, are copied unchanged.
DROP TABLE IF EXISTS invoices_old;
ALTER TABLE invoices RENAME TO invoices_old;
CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);
INSERT INTO invoices (id, customer_id, total_cents, created_at, status)
SELECT id, customer_id, total_cents, created_at,
       COALESCE((SELECT b.status FROM invoice_status_backup AS b WHERE b.id = invoices_old.id), 'open')
FROM invoices_old;
DROP TABLE invoices_old;

-- Rebuild payments with an enforced parent reference. Quarantined rows are
-- deliberately excluded; they remain intact in payment_orphans.
CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments_old AS p
JOIN invoices AS i ON i.id = p.invoice_id;
DROP TABLE payments_old;
 
INSERT OR REPLACE INTO invoice_status_backup (id, status)
SELECT id, status FROM invoices;
CREATE TRIGGER IF NOT EXISTS invoices_status_backup_sync
AFTER UPDATE OF status ON invoices
BEGIN
  INSERT OR REPLACE INTO invoice_status_backup (id, status)
  VALUES (NEW.id, NEW.status);
END;

COMMIT;
PRAGMA foreign_keys = ON;
