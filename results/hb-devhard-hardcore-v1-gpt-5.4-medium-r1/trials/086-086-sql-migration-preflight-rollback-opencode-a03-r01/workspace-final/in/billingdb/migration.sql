PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

-- Persist invoice status values so repeat runs can rebuild safely.
CREATE TABLE IF NOT EXISTS invoice_status_backup (
  invoice_id TEXT PRIMARY KEY,
  status TEXT NOT NULL
);

INSERT OR IGNORE INTO invoice_status_backup (invoice_id, status)
SELECT id, 'open'
FROM invoices;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans (id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at, 'missing_invoice'
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

DROP TRIGGER IF EXISTS invoices_status_backup_ai;
DROP TRIGGER IF EXISTS invoices_status_backup_au;
DROP TRIGGER IF EXISTS invoices_status_backup_ad;

ALTER TABLE invoices RENAME TO invoices__old;

CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices (id, customer_id, total_cents, created_at, status)
SELECT old.id,
       old.customer_id,
       old.total_cents,
       old.created_at,
       COALESCE(backup.status, 'open')
FROM invoices__old AS old
LEFT JOIN invoice_status_backup AS backup ON backup.invoice_id = old.id;

DROP TABLE invoices__old;

DELETE FROM invoice_status_backup
WHERE invoice_id NOT IN (SELECT id FROM invoices);

INSERT OR REPLACE INTO invoice_status_backup (invoice_id, status)
SELECT id, status
FROM invoices;

CREATE TRIGGER invoices_status_backup_ai
AFTER INSERT ON invoices
BEGIN
  INSERT OR REPLACE INTO invoice_status_backup (invoice_id, status)
  VALUES (NEW.id, NEW.status);
END;

CREATE TRIGGER invoices_status_backup_au
AFTER UPDATE OF id, status ON invoices
BEGIN
  DELETE FROM invoice_status_backup
  WHERE invoice_id = OLD.id
    AND OLD.id <> NEW.id;

  INSERT OR REPLACE INTO invoice_status_backup (invoice_id, status)
  VALUES (NEW.id, NEW.status);
END;

CREATE TRIGGER invoices_status_backup_ad
AFTER DELETE ON invoices
BEGIN
  DELETE FROM invoice_status_backup WHERE invoice_id = OLD.id;
END;

ALTER TABLE payments RENAME TO payments__old;

CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL REFERENCES invoices(id),
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments__old AS p
INNER JOIN invoices AS i ON i.id = p.invoice_id;

DROP TABLE payments__old;

COMMIT;

PRAGMA foreign_keys = ON;
