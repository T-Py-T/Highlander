-- Billing schema migration: add invoice status and enforce future payment references.
-- SQLite only. The transaction is intentionally explicit.
-- Foreign keys remain enabled; payments are rebuilt before invoices are replaced.

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Keep orphan rows outside payments before the new FK is installed.  The
-- uniqueness guard makes reruns harmless.
CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

INSERT OR IGNORE INTO payment_orphans (id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at,
       'invoice_id does not reference an existing invoice'
FROM payments AS p
WHERE NOT EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);

-- This small durable mapping lets a second execution rebuild the table while
-- retaining any status values that may have been assigned after migration.
-- It is removed by rollback.sql.
CREATE TABLE IF NOT EXISTS invoice_status (
  invoice_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT OR IGNORE INTO invoice_status (invoice_id, status)
SELECT id, 'open' FROM invoices;

-- Stage valid payments without a foreign key. The old child is then removed,
-- allowing the parent table to be replaced while FK enforcement stays enabled.
DROP TABLE IF EXISTS payments_stage;
CREATE TABLE payments_stage (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments_stage (id, invoice_id, amount_cents, created_at)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at
FROM payments AS p
WHERE EXISTS (SELECT 1 FROM invoices AS i WHERE i.id = p.invoice_id);

DROP TABLE payments;

-- Rebuild invoices from the common legacy columns and the durable status map.
-- The DEFAULT supplies open for every newly discovered invoice.
DROP TABLE IF EXISTS invoices_new;
CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices_new (id, customer_id, total_cents, created_at, status)
SELECT i.id, i.customer_id, i.total_cents, i.created_at,
       COALESCE(s.status, 'open')
FROM invoices AS i
LEFT JOIN invoice_status AS s ON s.invoice_id = i.id;

DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

-- Install the child FK only after the new parent exists.
DROP TABLE IF EXISTS payments_new;
CREATE TABLE payments_new (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT INTO payments_new (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at FROM payments_stage;

DROP TABLE payments_stage;
ALTER TABLE payments_new RENAME TO payments;

-- Keep the idempotence map synchronized if an application changes a status
-- between migration runs.
CREATE TRIGGER IF NOT EXISTS invoices_status_sync
AFTER UPDATE OF status ON invoices
BEGIN
  INSERT INTO invoice_status (invoice_id, status) VALUES (NEW.id, NEW.status)
  ON CONFLICT(invoice_id) DO UPDATE SET status = excluded.status;
END;

COMMIT;
PRAGMA foreign_keys = ON;
