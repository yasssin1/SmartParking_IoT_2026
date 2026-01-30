import paho.mqtt.client as mqtt
import json
import time
import requests

API_BASE = "http://localhost:3000" #a changer au hebergement

# --- CONFIGURATION À MODIFIER ---
BROKER = "broker.emqx.io"
PORT = 1883
# Chaque personne doit changer ce ID (ex: SmartPark2026_P1)
CLIENT_ID = "SmartPark2026_P6" 

# --- LOGIQUE DE RÉCEPTION ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        spot_id = payload.get("id")
        status = payload.get("status")
        if not spot_id or status not in ["FREE", "OCCUPIED"]:
            return

        r = requests.put(
            f"{API_BASE}/places/{spot_id}/status",
            json={"status": status},
            timeout=2
        )
        print(f"➡️ {msg.topic} {payload} -> REST {r.status_code} {r.text}")
        if r.status_code == 404:
            # Create spot then retry update
            requests.post(
                f"{API_BASE}/places",
                json={"id": spot_id, "label": spot_id},
                timeout=2
            )
            r = requests.put(
                f"{API_BASE}/places/{spot_id}/status",
                json={"status": status},
                timeout=2
            )



    except Exception as e:
        print(f"⚠️ Erreur de format : {e}")

# --- INITIALISATION ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, CLIENT_ID)
client.on_message = on_message

print(f"🔌 Connexion au broker {BROKER}...")
client.connect(BROKER, PORT)
client.subscribe("smart_parking_2026/parking/spots/+/status")


client.loop_forever()