"""
Smart Parking IoT 2026 - Person 2: Entry/Exit Logic
"""
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

# Configuration
CLIENT_ID = "SmartPark2026_P2"
BROKER = "broker.emqx.io"
PORT = 1883
PREFIX = "smart_parking_2026/"

# Topics for entry/exit sensors (from Person 1)
ENTRY_TOPIC = PREFIX + "parking/entry_sensor/status"
EXIT_TOPIC = PREFIX + "parking/exit_sensor/status"

# Global variables
available_spots = 0
total_spots = 20

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback API v2 - updated signature"""
    if reason_code == 0:
        print("=" * 60)
        print(f"Connected to {BROKER}")
        print(f"Client ID: {CLIENT_ID}")
        print("=" * 60)
        
        # Subscribe to parking spot status updates
        client.subscribe(PREFIX + "parking/spots/+/status")
        
        # Subscribe to available spots count
        client.subscribe(PREFIX + "parking/display/available")
        
        # Subscribe to entry/exit sensors
        client.subscribe(ENTRY_TOPIC)
        client.subscribe(EXIT_TOPIC)
        
        # Subscribe to barrier states (optional, for monitoring)
        client.subscribe(PREFIX + "parking/barriers/entry/state")
        client.subscribe(PREFIX + "parking/barriers/exit/state")
        
        print("Person 2 - Entry/Exit Logic ACTIVE!")
        print("Waiting for events...\n")
    else:
        print(f"Connection failed with reason code: {reason_code}")

def on_message(client, userdata, msg):
    global available_spots
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        print(f"\nReceived: {topic}")
        print(f"Data: {payload}")
        
        # Update available spots count
        if "display/available" in topic:
            available_spots = payload.get("count", 0)
            print(f"Available: {available_spots} spots")
        
        # Handle entry sensor
        elif topic == ENTRY_TOPIC:
            status = payload.get("status")
            ts = payload.get("ts")
            
            if status == "OCCUPIED":
                print(f"Vehicle detected at ENTRY at {ts}")
                handle_entry_request(client)
        
        # Handle exit sensor
        elif topic == EXIT_TOPIC:
            status = payload.get("status")
            ts = payload.get("ts")
            
            if status == "OCCUPIED":
                print(f"Vehicle detected at EXIT at {ts}")
                handle_exit_request(client)
        
        # Handle parking spot updates (for counting)
        elif "spots/" in topic and "/status" in topic:
            spot_id = payload.get("id")
            status = payload.get("status")
            distance_cm = payload.get("distance_cm")
            ts = payload.get("ts")
            
            print(f"Spot {spot_id}: {status} (distance={distance_cm}cm) at {ts}")
    
    except Exception as e:
        print(f"Error processing message: {e}")

def handle_entry_request(client):
    global available_spots
    
    print("\n" + "=" * 60)
    print("ENTRY REQUEST")
    print("=" * 60)
    print(f"Available spots: {available_spots}/{total_spots}")
    
    if available_spots > 0:
        print("✓ Opening ENTRY barrier")
        open_entry_barrier(client)
    else:
        print("✗ PARKING FULL - Barrier stays CLOSED")
    
    print("=" * 60)

def handle_exit_request(client):
    print("\n" + "=" * 60)
    print("EXIT REQUEST")
    print("=" * 60)
    print("✓ Opening EXIT barrier")
    open_exit_barrier(client)
    print("=" * 60)

def open_entry_barrier(client):
    topic = PREFIX + "parking/barriers/entry/cmd"
    command = {
        "action": "OPEN",
        "ts": datetime.now().isoformat(timespec="seconds")
    }
    client.publish(topic, json.dumps(command), qos=1)
    print(f"Command sent to {topic}: {command}")

def open_exit_barrier(client):
    topic = PREFIX + "parking/barriers/exit/cmd"
    command = {
        "action": "OPEN",
        "ts": datetime.now().isoformat(timespec="seconds")
    }
    client.publish(topic, json.dumps(command), qos=1)
    print(f"Command sent to {topic}: {command}")

def main():
    print("=" * 60)
    print("SMART PARKING - PERSON 2: ENTRY/EXIT LOGIC")
    print("=" * 60)
    
    # Use Callback API v2 (matching Person 1)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID
    )
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print(f"Connecting to {BROKER}:{PORT}...")
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nStopping...")
        client.disconnect()
        print("Goodbye!")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    main()