-- Billing schema migration v1.
-- Run as one SQLite script.  The status shadow table makes reruns preserve
-- statuses that callers may have changed after the first migration.
-- Rebuilding parent/child tables requires this connection-local toggle.
-- It is restored before the script finishes.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at, 'invoice does not exist'
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);

-- This small state table is internal migration bookkeeping.  It is removed
-- by rollback.sql and allows this script to be safely run more than once.
CREATE TABLE IF NOT EXISTS invoice_status_state (
  invoice_id TEXT PRIMARY KEY,
  status TEXT NOT NULL
);
INSERT OR IGNORE INTO invoice_status_state(invoice_id, status)
SELECT id, 'open' FROM invoices;

DROP TABLE IF EXISTS invoices_new;
CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);
INSERT INTO invoices_new(id, customer_id, total_cents, created_at, status)
SELECT i.id, i.customer_id, i.total_cents, i.created_at,
       COALESCE(s.status, 'open')
FROM invoices AS i
LEFT JOIN invoice_status_state AS s ON s.invoice_id = i.id;
DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

DROP TRIGGER IF EXISTS invoices_status_state_sync;
CREATE TRIGGER invoices_status_state_sync
AFTER UPDATE OF status ON invoices
BEGIN
  INSERT INTO invoice_status_state(invoice_id, status)
  VALUES (NEW.id, NEW.status)
  ON CONFLICT(invoice_id) DO UPDATE SET status = excluded.status;
END;

DROP TABLE IF EXISTS payments_new;
CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL REFERENCES invoices(id),
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO payments_new(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
WHERE EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);
DROP TABLE payments;
ALTER TABLE payments_new RENAME TO payments;

COMMIT;
PRAGMA foreign_keys = ON;
