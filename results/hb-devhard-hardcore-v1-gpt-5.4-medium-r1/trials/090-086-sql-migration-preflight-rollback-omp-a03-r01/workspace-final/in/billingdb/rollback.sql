BEGIN IMMEDIATE;

DROP TABLE IF EXISTS invoices__old;
DROP TABLE IF EXISTS payments__old;

CREATE TABLE invoices__old (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices__old (id, customer_id, total_cents, created_at)
SELECT
  id,
  customer_id,
  total_cents,
  created_at
FROM invoices;

CREATE TABLE payments__old (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments__old (id, invoice_id, amount_cents, created_at)
SELECT
  id,
  invoice_id,
  amount_cents,
  created_at
FROM payments;

INSERT OR IGNORE INTO payments__old (id, invoice_id, amount_cents, created_at)
SELECT
  id,
  invoice_id,
  amount_cents,
  created_at
FROM payment_orphans;

DROP TABLE payments;
DROP TABLE invoices;
DROP TABLE payment_orphans;
ALTER TABLE invoices__old RENAME TO invoices;
ALTER TABLE payments__old RENAME TO payments;

COMMIT;
