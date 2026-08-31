-- Billing migration. Run as a SQLite script (not piecemeal).
-- foreign_keys must be off only while the two tables are rebuilt; it is
-- restored before this script completes.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

-- This makes rebuilding invoices idempotent without referring to the status
-- column before it exists on the first run.
CREATE TABLE IF NOT EXISTS billing_invoice_status (
  invoice_id TEXT PRIMARY KEY,
  status TEXT NOT NULL
);
INSERT OR IGNORE INTO billing_invoice_status(invoice_id, status)
SELECT id, 'open' FROM invoices;

INSERT OR IGNORE INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at,
       'invoice_id does not exist in invoices at migration time'
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);

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
LEFT JOIN billing_invoice_status AS s ON s.invoice_id = i.id;
DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

DROP TABLE IF EXISTS payments_new;
CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO payments_new(id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
WHERE EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);
DROP TABLE payments;
ALTER TABLE payments_new RENAME TO payments;

CREATE TRIGGER IF NOT EXISTS billing_invoice_status_sync
AFTER UPDATE OF status ON invoices
BEGIN
  INSERT INTO billing_invoice_status(invoice_id, status)
  VALUES (NEW.id, NEW.status)
  ON CONFLICT(invoice_id) DO UPDATE SET status = excluded.status;
END;

COMMIT;
PRAGMA foreign_keys = ON;
