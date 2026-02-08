import paho.mqtt.client as mqtt
import json
import requests

API_BASE = "http://localhost:3000"

BROKER = "broker.emqx.io"
PORT = 1883
CLIENT_ID = "SmartPark2026_P6"

TOPIC_SPOTS = "smart_parking_2026/parking/spots/+/status"
TOPIC_BARRIER_STATE = "smart_parking_2026/parking/barriers/+/state"
TOPIC_NEW_SPOT = "smart_parking_2026/parking/config/new_spot"

# Avoid publishing ADD repeatedly on restart
published_spots = set()

def build_update_payload(payload: dict):
    out = {"status": payload.get("status")}

    # sensor -> backend mapping
    dc = payload.get("distance_cm")
    tc = payload.get("threshold_cm")
    dn = payload.get("debounce_n")

    if isinstance(dc, (int, float)):
        out["distance"] = float(dc)
    if isinstance(tc, (int, float)):
        out["threshold"] = float(tc)
    if isinstance(dn, int):
        out["debounce"] = dn

    return out
#########################
#fonctions de traitemens#
#########################
def topic_barrier_id(topic: str):
    # smart_parking_2026/parking/barriers/{id}/state
    parts = topic.split("/")
    return parts[-2] if len(parts) >= 2 else None

def publish_new_spot(mqtt_client, spot_id: str):
    if spot_id in published_spots:
        return
    payload = {"id": spot_id, "cmd": "ADD"}
    mqtt_client.publish(TOPIC_NEW_SPOT, json.dumps(payload), retain=False)
    published_spots.add(spot_id)
    print(f"📤 published new_spot -> {TOPIC_NEW_SPOT} {payload}")

def forward_spot(mqtt_client, payload: dict, topic: str):
    spot_id = payload.get("id")
    status = payload.get("status")
    if not spot_id or status not in ["FREE", "OCCUPIED"]:
        return

    update_body = build_update_payload(payload)

    r = requests.put(f"{API_BASE}/places/{spot_id}/status", json=update_body, timeout=2)
    print(f"➡️ {topic} -> REST {r.status_code}")

    if r.status_code == 404:
        create_body = {"id": spot_id, "label": payload.get("label") or spot_id}
        for k in ("distance", "threshold", "debounce"):
            if k in update_body:
                create_body[k] = update_body[k]

        create_resp = requests.post(f"{API_BASE}/places", json=create_body, timeout=2)

        # If created (201) OR already exists (409), publish config/new_spot once
        if create_resp.status_code in (201, 409, 200):
            publish_new_spot(mqtt_client, spot_id)

        r = requests.put(f"{API_BASE}/places/{spot_id}/status", json=update_body, timeout=2)
        print(f"🔁 retry -> REST {r.status_code}")

def forward_barrier_state(payload: dict, topic: str):
    state = payload.get("state")
    if state not in ["OPENING", "OPENED", "CLOSING", "CLOSED"]:
        return

    barrier_id = topic_barrier_id(topic)
    if not barrier_id:
        return

    r = requests.put(
        f"{API_BASE}/barrier/{barrier_id}/state",
        json={"state": state},
        timeout=2
    )
    print(f"🚧 {topic} state={state} -> REST {r.status_code}")

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"✅ Connected: reason_code={reason_code}")
    client.subscribe(TOPIC_SPOTS)
    client.subscribe(TOPIC_BARRIER_STATE)
    print(f"✅ Subscribed to {TOPIC_SPOTS}")
    print(f"✅ Subscribed to {TOPIC_BARRIER_STATE}")


######
#main#
######
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic

        if "/parking/spots/" in topic and topic.endswith("/status"):
            forward_spot(client, payload, topic)
        elif "/parking/barriers/" in topic and topic.endswith("/state"):
            forward_barrier_state(payload, topic)

    except Exception as e:
        print(f"⚠️ Error: {e}")

client = mqtt.Client(client_id=CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message

print(f"🔌 Connecting to {BROKER}:{PORT} ...")
client.connect(BROKER, PORT)
client.loop_forever()
