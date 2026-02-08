import paho.mqtt.client as mqtt

BROKER="broker.emqx.io"
PORT=1883
CLIENT_ID="SmartPark2026_SUB_NEWSPOT"
TOPIC="smart_parking_2026/parking/config/new_spot"

def on_message(client, userdata, msg):
    print("[NEW_SPOT]", msg.topic, "->", msg.payload.decode())

c = mqtt.Client(client_id=CLIENT_ID)
c.on_message = on_message
c.connect(BROKER, PORT)
c.subscribe(TOPIC)
print("listening:", TOPIC)
c.loop_forever()
