PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS _billing_migration_backup_invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO _billing_migration_backup_invoices (id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices;

CREATE TABLE IF NOT EXISTS _billing_migration_backup_payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT OR IGNORE INTO _billing_migration_backup_payments (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments;

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
       'missing invoice during billing migration'
FROM _billing_migration_backup_payments AS p
LEFT JOIN _billing_migration_backup_invoices AS i
  ON i.id = p.invoice_id
WHERE i.id IS NULL;

DROP TABLE IF EXISTS invoices_migrated;

CREATE TABLE invoices_migrated (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices_migrated (id, customer_id, total_cents, created_at, status)
SELECT id,
       customer_id,
       total_cents,
       created_at,
       'open'
FROM _billing_migration_backup_invoices;

DROP TABLE IF EXISTS payments_migrated;

CREATE TABLE payments_migrated (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices_migrated(id)
);

INSERT INTO payments_migrated (id, invoice_id, amount_cents, created_at)
SELECT p.id,
       p.invoice_id,
       p.amount_cents,
       p.created_at
FROM _billing_migration_backup_payments AS p
INNER JOIN _billing_migration_backup_invoices AS i
  ON i.id = p.invoice_id;

DROP TABLE payments;
DROP TABLE invoices;

ALTER TABLE invoices_migrated RENAME TO invoices;
ALTER TABLE payments_migrated RENAME TO payments;

COMMIT;

PRAGMA foreign_keys = ON;
