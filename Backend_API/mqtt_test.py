import paho.mqtt.client as mqtt
import json
import time

BROKER = "broker.emqx.io"
PORT = 1883
CLIENT_ID = "SmartPark2026_PUB_TEST"

def publish_once(spot_id, status, retain=False):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, CLIENT_ID)
    client.connect(BROKER, PORT)
    topic = f"smart_parking_2026/parking/spots/{spot_id}/status"
    payload = {"id": spot_id, "status": status}
    client.publish(topic, json.dumps(payload), retain=retain)
    client.disconnect()
    print(f"[PUB] {topic} <- {payload} retain={retain}")

if __name__ == "__main__":
    publish_once("A01", "OCCUPIED", retain=False)

