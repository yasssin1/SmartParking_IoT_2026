from flask import Flask, jsonify, request
import json
import paho.mqtt.client as mqtt

app = Flask(__name__)
# Spots normalized to A01..A20
SPOTS = [f"A{i:02d}" for i in range(1, 21)]  
places = {sid: "FREE" for sid in SPOTS}
# ----------------------------
# CONFIG
# ----------------------------
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

PREFIX = "smart_parking_2026"

MQTT_TOPIC = f"{PREFIX}/parking/spots/+/status"
MQTT_LED_TOPIC = f"{PREFIX}/parking/display/available"

mqtt_client = None

# ----------------------------
# MQTT CALLBACKS (API v2)
# ----------------------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    # Subscribe to all spot status updates
    client.subscribe(MQTT_TOPIC, qos=1)
    

def on_message(client, userdata, msg):
    
    # topic: smart_parking_2026/parking/spots/<id>/status

    parts = msg.topic.split("/")
    if len(parts) < 5:
        return

    raw_id = parts[3].upper()
    if not (raw_id.startswith("A") and raw_id[1:].isdigit()):
        return
    place_id = f"A{int(raw_id[1:]):02d}"


    payload = msg.payload.decode("utf-8").strip()

    # Accept JSON payload or plain text (FREE/OCCUPIED)
    status = None

    try:
        data = json.loads(payload)
        status = str(data.get("status", "")).upper()

        # Informations supplémentaires envoyées par P1 (acceptées uniquement pour compatibilité)

        distance_cm = data.get("distance_cm", None)
        ts = data.get("ts", None)
        
        if "id" in data:
            incoming = str(data["id"]).upper()
            if incoming.startswith("A") and incoming[1:].isdigit():
                place_id = f"A{int(incoming[1:]):02d}"

    except Exception:
        status = payload.upper()


    if status not in ("FREE", "OCCUPIED"):
        return

    places[place_id] = status

    publish_led_summary()


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
            width: 420px;
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
            margin-top: 20px;
            font-size: 22px;
            color: #ffcc00;
        }
        .hint {
            margin-top: 10px;
            font-size: 12px;
            color: #9aa4b2;
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
        

    </div>

    <script>
        async function update() {
            const r = await fetch('/api/parking/summary');
            const data = await r.json();

            document.getElementById('free').innerText = data.free + " / " + data.total;

            if (data.free === 0) {
                document.getElementById('state').innerText = "Parking complet";
            } else {
                document.getElementById('state').innerText = "Places disponibles";
            }
        }

        update();
        setInterval(update, 2000);


    </script>
</body>
</html>
"""


@app.get("/api/parking/places")
def get_places():
    return jsonify([{"id": pid, "status": status} for pid, status in places.items()])

@app.get("/api/parking/summary")
def get_summary():
    total = len(places)
    occupied = sum(1 for s in places.values() if s == "OCCUPIED")
    free = total - occupied
    return jsonify({"total": total, "occupied": occupied, "free": free})

def publish_led_summary():
    if mqtt_client is None:
        return
    total = len(places)
    occupied = sum(1 for s in places.values() if s == "OCCUPIED")
    free = total - occupied

    payload = {"count": free}
    mqtt_client.publish(MQTT_LED_TOPIC, json.dumps(payload), qos=1, retain=True)



@app.post("/api/parking/places/<pid>/status")
def set_status(pid):
    data = request.get_json(force=True)
    status = data.get("status", "").upper()
    if status not in ("FREE", "OCCUPIED"):
        return jsonify({"ok": False, "error": "status must be FREE or OCCUPIED"}), 400
    if pid not in places:
        return jsonify({"ok": False, "error": "unknown placeId"}), 404
    places[pid] = status

    publish_led_summary()

    return jsonify({"ok": True, "id": pid, "status": status})

@app.post("/api/parking/places")
def add_place():
    data = request.get_json(force=True)
    pid = data.get("id", "").upper()
    if not pid:
        return jsonify({"ok": False, "error": "id required"}), 400
    if pid in places:
        return jsonify({"ok": False, "error": "already exists"}), 400
    places[pid] = "FREE"
    publish_led_summary()

    return jsonify({"ok": True, "id": pid})



if __name__ == "__main__":
    start_mqtt()
    app.run(host="127.0.0.1", port=3000, debug=True, use_reloader=False)
