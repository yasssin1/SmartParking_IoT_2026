const express = require("express");
const Database = require("better-sqlite3");
const fs = require("fs");

const app = express();
app.use(express.json());

// cree base donnee
const db = new Database("parking.db");
const schema = fs.readFileSync("./database/schema.sql", "utf-8");
db.exec(schema);

function nowIso() {
  return new Date().toISOString();
}
// ---------------
// ---FONCTIONS---
// ---------------

// ajouter place
app.post("/places", (req, res) => {
  const { id, label } = req.body || {};
  if (!id || typeof id !== "string") {
    return res.status(400).json({ error: "INVALID_ID", message: "id is required (string)" });
  }

  const stmt = db.prepare(
    "INSERT INTO spots (id, label, status, updated_at) VALUES (?, ?, 'FREE', ?)"
  );

  try {
    stmt.run(id, label ?? id, nowIso());
    return res.status(201).json({ id, label: label ?? id, status: "FREE" });
  } catch (e) {
    if (String(e).includes("UNIQUE")) {
      return res.status(409).json({ error: "ALREADY_EXISTS", message: `Spot ${id} already exists` });
    }
    return res.status(500).json({ error: "DB_ERROR", message: "Failed to create spot" });
  }
});

// requete liste de places
app.get("/places", (req, res) => {
  const rows = db.prepare("SELECT id, label, status, updated_at FROM spots ORDER BY id").all();
  res.json(rows);
});

// requete chercher place par {id}
app.get("/places/:id", (req, res) => {
  const row = db.prepare("SELECT id, label, status, updated_at FROM spots WHERE id = ?").get(req.params.id);
  if (!row) return res.status(404).json({ error: "NOT_FOUND", message: "Spot not found" });
  res.json(row);
});

// requete chercher status place par {id}
app.get("/places/:id/status", (req, res) => {
  const row = db.prepare("SELECT status FROM spots WHERE id = ?").get(req.params.id);
  if (!row) return res.status(404).json({ error: "NOT_FOUND", message: "Spot not found" });
  res.json(row);
});

//change status dun place
app.put("/places/:id/status", (req, res) => {
  const { status } = req.body || {};
  if (!["FREE", "OCCUPIED"].includes(status)) {
    return res.status(400).json({ error: "INVALID_STATUS" });
  }

  const ts = nowIso();
  const info = db
    .prepare("UPDATE spots SET status = ?, updated_at = ? WHERE id = ?")
    .run(status, ts, req.params.id);

  if (info.changes === 0) {
    return res.status(404).json({ error: "NOT_FOUND", message: "Spot not found" });
  }
  res.json({ id: req.params.id, status, updated_at: ts });
});

// requete chercher liste place non occupee
app.get("/parking/available", (req, res) => {
  const row = db.prepare("SELECT id FROM spots WHERE status='FREE'").all();
  if (!row) return res.status(404).json({ error: "NOT_FOUND", message: "Spot not found" });
  res.json(row);
});

// info generale {nbr total, nbr 'free', nbr 'occupee'}
app.get("/parking/state", (req, res) => {
  const r = db.prepare(`
    SELECT
      COUNT(*) AS total,
      SUM(CASE WHEN status='FREE' THEN 1 ELSE 0 END) AS free,
      SUM(CASE WHEN status='OCCUPIED' THEN 1 ELSE 0 END) AS occupied
    FROM spots
  `).get();

  res.json({
    total: r.total || 0,
    free: r.free || 0,
    occupied: r.occupied || 0
  });
});

//-------------
//---barrier---
//-------------

//chercher status barrier par id
app.get("/barrier/:id", (req, res) => {
  const row = db.prepare("SELECT status, updated_at FROM barriers WHERE id = ?").get(req.params.id);
  if (!row) return res.status(404).json({ error: "NOT_FOUND", message: "Spot not found" });
  res.json(row);
});

//fonction gerer barrier
function setBarrierState(id, state) {
  const ts = nowIso();
  const stmt = db.prepare(`
    INSERT INTO barriers (id, state, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at
  `);
  stmt.run(id, state, ts);
  return { id, state, updated_at: ts };
}

app.post("/barrier/:id/open", (req, res) => {
  const out = setBarrierState(req.params.id, "OPENED");
  res.json({ ok: true, ...out });
});

app.post("/barrier/:id/close", (req, res) => {
  const out = setBarrierState(req.params.id, "CLOSED");
  res.json({ ok: true, ...out });
});

// --- start ---
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`REST API running on http://localhost:${PORT}`));
