-- Billing schema migration. Run as one SQLite script.
-- foreign_keys is restored before this script finishes; the transaction is
-- explicit so a caller can roll it back if any statement fails.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

-- INSERT OR IGNORE makes repeated runs harmless and retains historical orphans.
INSERT OR IGNORE INTO payment_orphans(id, invoice_id, amount_cents, created_at, reason)
SELECT p.id, p.invoice_id, p.amount_cents, p.created_at, 'missing invoice'
FROM payments AS p
LEFT JOIN invoices AS i ON i.id = p.invoice_id
WHERE i.id IS NULL;

-- Rebuild payments with the future foreign-key invariant. Invalid historical
-- rows have already been copied to payment_orphans.
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

-- Rebuild invoices so this is also repeatable on an already-migrated DB.
DROP TABLE IF EXISTS invoices_new;
CREATE TABLE invoices_new (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);
INSERT INTO invoices_new(id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at FROM invoices;
DROP TABLE invoices;
ALTER TABLE invoices_new RENAME TO invoices;

COMMIT;
PRAGMA foreign_keys = ON;
