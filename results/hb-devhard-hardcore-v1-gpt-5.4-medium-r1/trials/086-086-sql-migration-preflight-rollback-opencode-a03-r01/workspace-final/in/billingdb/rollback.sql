PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TRIGGER IF EXISTS invoices_status_backup_ai;
DROP TRIGGER IF EXISTS invoices_status_backup_au;
DROP TRIGGER IF EXISTS invoices_status_backup_ad;

ALTER TABLE invoices RENAME TO invoices__rollback_old;

CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices (id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices__rollback_old;

DROP TABLE invoices__rollback_old;

ALTER TABLE payments RENAME TO payments__rollback_old;

CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments__rollback_old;

INSERT OR IGNORE INTO payments (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payment_orphans;

DROP TABLE payments__rollback_old;
DROP TABLE IF EXISTS payment_orphans;
DROP TABLE IF EXISTS invoice_status_backup;

COMMIT;

PRAGMA foreign_keys = OFF;
