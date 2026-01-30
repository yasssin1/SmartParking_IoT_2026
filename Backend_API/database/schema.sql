CREATE TABLE IF NOT EXISTS spots (
  id         TEXT PRIMARY KEY,
  label      TEXT,
  status     TEXT NOT NULL CHECK (status IN ('FREE','OCCUPIED')),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS barriers (
  id         TEXT PRIMARY KEY,
  state      TEXT NOT NULL CHECK (state IN ('OPENED','CLOSED')),
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_spots_status ON spots(status);
