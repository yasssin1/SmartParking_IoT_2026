import paho.mqtt.client as mqtt
import json
import time
import threading

# --- CONFIGURATION ---
BROKER = "broker.emqx.io"
PORT = 1883
CLIENT_ID = "SmartPark2026_P3"
PREFIX = "smart_parking_2026/"

# TOPICS
# We subscribe to BOTH entry and exit commands using a wildcard '+'
TOPIC_CMD_WILDCARD = PREFIX + "parking/barriers/+/cmd"

# --- BARRIER SIMULATION ---
def move_barrier_sequence(client, barrier_type):
    """
    Simulates the movement of a specific barrier (ENTRY or EXIT).
    barrier_type should be "entry" or "exit".
    """
    topic_state = f"{PREFIX}parking/barriers/{barrier_type}/state"
    
    print(f"\n[🚀 {barrier_type.upper()}] Received OPEN command. Moving barrier...")

    # 1. OPENING
    client.publish(topic_state, json.dumps({"state": "OPENING"}))
    print(f"[⚙️ {barrier_type.upper()}] Status: OPENING... (2s)")
    time.sleep(2)

    # 2. OPENED
    client.publish(topic_state, json.dumps({"state": "OPENED"}))
    print(f"[✅ {barrier_type.upper()}] Status: OPENED. Waiting for car (5s)...")
    time.sleep(5)

    # 3. CLOSING
    client.publish(topic_state, json.dumps({"state": "CLOSING"}))
    print(f"[⚙️ {barrier_type.upper()}] Status: CLOSING... (2s)")
    time.sleep(2)

    # 4. CLOSED
    client.publish(topic_state, json.dumps({"state": "CLOSED"}))
    print(f"[⛔ {barrier_type.upper()}] Status: CLOSED. Ready.")

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ Connected to {BROKER} as {CLIENT_ID}")
        # Subscribe to ANY barrier command (entry OR exit)
        client.subscribe(TOPIC_CMD_WILDCARD)
        print(f"👂 Listening to: {TOPIC_CMD_WILDCARD}")
    else:
        print(f"⚠️ Connection failed: {reason_code}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        # Determine if it's ENTRY or EXIT based on the topic string
        # Topic format: .../parking/barriers/{TYPE}/cmd
        if "entry/cmd" in topic:
            barrier_type = "entry"
        elif "exit/cmd" in topic:
            barrier_type = "exit"
        else:
            return # Unknown topic

        # Check for OPEN command
        if payload.get("action") == "OPEN":
            # Run in a thread so we don't block the other barrier!
            t = threading.Thread(target=move_barrier_sequence, args=(client, barrier_type))
            t.start()
            
    except Exception as e:
        print(f"Error: {e}")

# --- MAIN ---
if __name__ == "__main__":
    # VERSION 2 FIX included here
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    print("🔌 Connecting to broker...")
    client.connect(BROKER, PORT, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping Barrier Module.")
        client.disconnect()