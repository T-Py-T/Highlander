PRAGMA foreign_keys = OFF;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS payment_orphans (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  reason TEXT NOT NULL
);

-- Keep invoice statuses in sync across reruns so the migration stays idempotent.
CREATE TABLE IF NOT EXISTS _invoice_status_shadow (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL
);

DROP TRIGGER IF EXISTS invoices_status_shadow_ai;
DROP TRIGGER IF EXISTS invoices_status_shadow_au;
DROP TRIGGER IF EXISTS invoices_status_shadow_ad;

ALTER TABLE invoices RENAME TO invoices__migration_source;

CREATE TABLE invoices (
  id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
);

INSERT INTO invoices (id, customer_id, total_cents, created_at, status)
SELECT
  source.id,
  source.customer_id,
  source.total_cents,
  source.created_at,
  COALESCE(shadow.status, 'open')
FROM invoices__migration_source AS source
LEFT JOIN _invoice_status_shadow AS shadow
  ON shadow.id = source.id;

INSERT OR REPLACE INTO _invoice_status_shadow (id, status)
SELECT id, status
FROM invoices;

DELETE FROM _invoice_status_shadow
WHERE id NOT IN (SELECT id FROM invoices);

CREATE TRIGGER invoices_status_shadow_ai
AFTER INSERT ON invoices
BEGIN
  INSERT OR REPLACE INTO _invoice_status_shadow (id, status)
  VALUES (NEW.id, NEW.status);
END;

CREATE TRIGGER invoices_status_shadow_au
AFTER UPDATE OF status ON invoices
BEGIN
  INSERT OR REPLACE INTO _invoice_status_shadow (id, status)
  VALUES (NEW.id, NEW.status);
END;

CREATE TRIGGER invoices_status_shadow_ad
AFTER DELETE ON invoices
BEGIN
  DELETE FROM _invoice_status_shadow WHERE id = OLD.id;
END;

DROP TABLE invoices__migration_source;

ALTER TABLE payments RENAME TO payments__migration_source;

CREATE TABLE payments (
  id TEXT PRIMARY KEY,
  invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

INSERT INTO payment_orphans (id, invoice_id, amount_cents, created_at, reason)
SELECT
  source.id,
  source.invoice_id,
  source.amount_cents,
  source.created_at,
  'Missing invoice during billing migration'
FROM payments__migration_source AS source
LEFT JOIN invoices AS i
  ON i.id = source.invoice_id
WHERE i.id IS NULL
  AND NOT EXISTS (
    SELECT 1
    FROM payment_orphans AS existing
    WHERE existing.id = source.id
  );

INSERT INTO payments (id, invoice_id, amount_cents, created_at)
SELECT
  source.id,
  source.invoice_id,
  source.amount_cents,
  source.created_at
FROM payments__migration_source AS source
WHERE EXISTS (
  SELECT 1
  FROM invoices AS i
  WHERE i.id = source.invoice_id
)
  AND NOT EXISTS (
    SELECT 1
    FROM payments AS existing
    WHERE existing.id = source.id
  );

DROP TABLE payments__migration_source;

COMMIT;

PRAGMA foreign_keys = ON;
