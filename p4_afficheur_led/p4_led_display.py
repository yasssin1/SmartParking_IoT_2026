from flask import Flask, jsonify
import json
from datetime import datetime
import paho.mqtt.client as mqtt
import time

app = Flask(__name__)

# ----------------------------
# MODÈLE DE DONNÉES (Read-only)
# ----------------------------
SPOTS = [f"A{i:02d}" for i in range(1, 21)]  # A01..A20
places = {sid: "FREE" for sid in SPOTS}

# ----------------------------
# CONFIG MQTT
# ----------------------------
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
PREFIX = "smart_parking_2026"

# P1 -> états des places
MQTT_SPOTS_TOPIC = f"{PREFIX}/parking/spots/+/status"

# P4 -> résumé (pour P2 / P7)
MQTT_LED_TOPIC = f"{PREFIX}/parking/display/available"

# P2 -> ordres barrière (CMD). On écoute juste pour l’UI (barrière globale).
MQTT_ENTRY_CMD_TOPIC = f"{PREFIX}/parking/barriers/entry/cmd"
MQTT_EXIT_CMD_TOPIC  = f"{PREFIX}/parking/barriers/exit/cmd"

mqtt_client = None

# ----------------------------
# ÉTAT BARrière (GLOBAL - UI)
# ----------------------------
barrier_state = "CLOSED"          # "OPENED" / "CLOSED"
barrier_last_open_ts = 0.0        # time.time() quand on reçoit OPEN
BARRIER_OPEN_SECONDS = 3.0        # durée d’affichage "OUVERTE" après un OPEN


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _normalize_place_id(raw) -> str | None:
    """Normalise l'ID en A01..A20 (accepte A1 ou A01)."""
    if raw is None:
        return None
    raw = str(raw).upper().strip()
    if not (raw.startswith("A") and raw[1:].isdigit()):
        return None
    return f"A{int(raw[1:]):02d}"


def publish_led_summary():
    """Publie {count: free} sur MQTT (retain=True) pour les autres modules."""
    if mqtt_client is None:
        return

    total = len(places)
    occupied = sum(1 for s in places.values() if s == "OCCUPIED")
    free = total - occupied

    payload = {"count": free, "ts": _now_iso()}
    mqtt_client.publish(MQTT_LED_TOPIC, json.dumps(payload), qos=1, retain=True)


def _update_barrier_timeout():
    """Si aucun OPEN récent, repasse la barrière en CLOSED."""
    global barrier_state
    if barrier_state == "OPENED":
        if (time.time() - barrier_last_open_ts) >= BARRIER_OPEN_SECONDS:
            barrier_state = "CLOSED"


# ----------------------------
# MQTT CALLBACKS (Callback API v2)
# ----------------------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    # Abonnements
    client.subscribe(MQTT_SPOTS_TOPIC, qos=1)
    client.subscribe(MQTT_ENTRY_CMD_TOPIC, qos=1)
    client.subscribe(MQTT_EXIT_CMD_TOPIC, qos=1)


def on_message(client, userdata, msg):
    global barrier_state, barrier_last_open_ts

    topic = msg.topic
    payload_str = msg.payload.decode("utf-8", errors="ignore").strip()

    # ---- 1) État des places (P1) ----
    if "/parking/spots/" in topic and topic.endswith("/status"):
        parts = topic.split("/")
        if len(parts) < 5:
            return

        place_id = _normalize_place_id(parts[3])
        if place_id is None:
            return

        status = None
        try:
            data = json.loads(payload_str)
            status = str(data.get("status", "")).upper()

            # Compatibilité : si "id" existe aussi dans le JSON, on le normalise
            incoming_id = _normalize_place_id(data.get("id"))
            if incoming_id is not None:
                place_id = incoming_id

            # Champs additionnels P1 acceptés (non utilisés)
            # distance_cm = data.get("distance_cm")
            # ts = data.get("ts")

        except Exception:
            status = payload_str.upper()

        if status not in ("FREE", "OCCUPIED"):
            return

        if place_id in places:
            places[place_id] = status
            publish_led_summary()
        return

    # ---- 2) CMD barrière (P2) -> UI globale ----
    
    if topic in (MQTT_ENTRY_CMD_TOPIC, MQTT_EXIT_CMD_TOPIC):
        try:
            data = json.loads(payload_str)
            action = str(data.get("action", "")).upper()
        except Exception:
            action = payload_str.upper()

        if action == "OPEN":
            barrier_state = "OPENED"
            barrier_last_open_ts = time.time()
        # Si un jour vous publiez "CLOSE", vous pouvez décommenter:
        # elif action in ("CLOSE", "CLOSED"):
        #     barrier_state = "CLOSED"
        return


def start_mqtt():
    global mqtt_client
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="SmartPark2026_P4"
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    mqtt_client = client


# ----------------------------
# API REST (Read-only)
# ----------------------------
@app.get("/api/parking/summary")
def get_summary():
    _update_barrier_timeout()
    total = len(places)
    occupied = sum(1 for s in places.values() if s == "OCCUPIED")
    free = total - occupied
    return jsonify({"total": total, "occupied": occupied, "free": free})


@app.get("/api/barrier")
def get_barrier():
    _update_barrier_timeout()
    return jsonify({
        "state": barrier_state,  # OPENED / CLOSED
        "ts": _now_iso()
    })


# ----------------------------
# WEB UI (Read-only)
# ----------------------------
@app.get("/")
def led_display():
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Afficheur LED - Smart Parking</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0b0f14;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .panel {
            background: #111827;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 0 30px rgba(0,0,0,0.6);
            text-align: center;
            width: 460px;
        }
        h1 {
            margin-bottom: 20px;
            font-size: 20px;
            color: #30ff88;
        }
        .count {
            font-size: 56px;
            font-weight: bold;
            letter-spacing: 1px;
        }
        .label {
            font-size: 16px;
            color: #cfcfcf;
            margin-top: 6px;
        }
        .status {
            margin-top: 16px;
            font-size: 22px;
            color: #ffcc00;
        }
        .hint {
            margin-top: 10px;
            font-size: 12px;
            color: #9aa4b2;
        }

        .barrier-wrap {
            margin-top: 18px;
            display: flex;
            justify-content: center;
            gap: 14px;
            align-items: center;
        }
        .dot {
            width: 18px;
            height: 18px;
            border-radius: 999px;
            background: #ef4444; /* rouge par défaut */
            box-shadow: 0 0 12px rgba(239,68,68,0.6);
        }
        .dot.open {
            background: #22c55e; /* vert */
            box-shadow: 0 0 12px rgba(34,197,94,0.6);
        }
        .barrier-text {
            text-align: left;
        }
        .barrier-title {
            font-size: 14px;
            color: #cfcfcf;
        }
        .barrier-state {
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }
    </style>
</head>
<body>
    <div class="panel">
        <h1>Afficheur LED – Parking Intelligent</h1>

        <div class="count" id="free">-- / --</div>
        <div class="label">Places libres</div>

        <div class="status" id="state">Chargement...</div>
        <div class="hint">Mise à jour automatique (toutes les 2 secondes)</div>

        <div class="barrier-wrap">
            <div class="dot" id="barDot"></div>
            <div class="barrier-text">
                <div class="barrier-title">Barrière</div>
                <div class="barrier-state" id="barState">CLOSED</div>
            </div>
        </div>
    </div>

    <script>
        async function update() {
            // ---- Parking summary ----
            const r = await fetch('/api/parking/summary');
            const data = await r.json();

            document.getElementById('free').innerText = data.free + " / " + data.total;

            if (data.free === 0) {
                document.getElementById('state').innerText = "Parking complet";
            } else {
                document.getElementById('state').innerText = "Places disponibles";
            }

            // ---- Barrier state ----
            const b = await fetch('/api/barrier');
            const bd = await b.json();

            const dot = document.getElementById('barDot');
            const txt = document.getElementById('barState');

            txt.innerText = bd.state;

            if (bd.state === "OPENED") {
                dot.classList.add('open');
            } else {
                dot.classList.remove('open');
            }
        }

        update();
        setInterval(update, 2000);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    start_mqtt()
    publish_led_summary()  # Publie une première valeur au démarrage (optionnel)
    app.run(host="127.0.0.1", port=3000, debug=True, use_reloader=False)
