import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timezone
import argparse

BROKER = "broker.emqx.io"
PORT = 1883
CLIENT_ID = "SmartPark2026_PUB_TEST"

def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def publish_sensor_like(client, spot_id, status, distance_cm=None, threshold_cm=50.0, debounce_n=4, retain=False):
    topic = f"smart_parking_2026/parking/spots/{spot_id}/status"
    payload = {
        "id": spot_id,
        "status": status,
        "threshold_cm": float(threshold_cm),
        "debounce_n": int(debounce_n),
        "ts": iso_now(),
    }
    if distance_cm is not None:
        payload["distance_cm"] = float(distance_cm)

    client.publish(topic, json.dumps(payload), retain=retain)
    print(f"[PUB] {topic} <- {payload} retain={retain}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", default="A01", help="Spot id, e.g. A01")
    parser.add_argument("--retain", action="store_true", help="Publish retained messages")
    parser.add_argument("--loop", type=int, default=0, help="Number of OCCUPIED<->FREE toggles (0 = just one publish)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between toggles in seconds")
    args = parser.parse_args()

    client = mqtt.Client(client_id=CLIENT_ID)  # v2 style, no callback warning
    client.connect(BROKER, PORT)

    if args.loop > 0:
        for i in range(args.loop):
            publish_sensor_like(client, args.id, "OCCUPIED", distance_cm=18.5, retain=args.retain)
            time.sleep(args.delay)
            publish_sensor_like(client, args.id, "FREE", distance_cm=200.0, retain=args.retain)
            time.sleep(args.delay)
    else:
        # Single publish (change to OCCUPIED if you want)
        publish_sensor_like(client, args.id, "FREE", distance_cm=200.0, retain=args.retain)

    client.disconnect()

if __name__ == "__main__":
    main()
