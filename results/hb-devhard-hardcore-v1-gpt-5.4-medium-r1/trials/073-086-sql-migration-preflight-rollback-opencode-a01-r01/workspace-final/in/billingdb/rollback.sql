PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

DROP TRIGGER IF EXISTS invoices_status_shadow_ai;
DROP TRIGGER IF EXISTS invoices_status_shadow_au;
DROP TRIGGER IF EXISTS invoices_status_shadow_ad;

ALTER TABLE invoices RENAME TO invoices__rollback_source;

CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO invoices (id, customer_id, total_cents, created_at)
SELECT id, customer_id, total_cents, created_at
FROM invoices__rollback_source;

DROP TABLE invoices__rollback_source;

ALTER TABLE payments RENAME TO payments__rollback_source;

CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT id, invoice_id, amount_cents, created_at
FROM payments__rollback_source;

INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT orphan.id, orphan.invoice_id, orphan.amount_cents, orphan.created_at
FROM payment_orphans AS orphan
WHERE NOT EXISTS (
  SELECT 1
  FROM payments AS existing
  WHERE existing.id = orphan.id
);

DROP TABLE payments__rollback_source;
DROP TABLE IF EXISTS payment_orphans;
DROP TABLE IF EXISTS _invoice_status_shadow;

COMMIT;

PRAGMA foreign_keys = ON;
