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

# Global variables
available_spots = 0
total_spots = 20

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("=" * 60)
        print(f"Connected to {BROKER}")
        print(f"Client ID: {CLIENT_ID}")
        print("=" * 60)
        
        client.subscribe(PREFIX + "parking/spots/+/status")
        client.subscribe(PREFIX + "parking/display/available")
        client.subscribe(PREFIX + "parking/barriers/entry/state")
        
        print("Person 2 - Entry/Exit Logic ACTIVE!")
        print("Waiting for events...\n")

def on_message(client, userdata, msg):
    global available_spots
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        print(f"\nReceived: {topic}")
        print(f"Data: {payload}")
        
        if "display/available" in topic:
            available_spots = payload.get("count", 0)
            print(f"Available: {available_spots} spots")
        
        elif "spots/" in topic and "/status" in topic:
            spot_id = payload.get("id")
            status = payload.get("status")
            
            if status == "OCCUPIED" and "ENTRY" in spot_id.upper():
                print("Vehicle at ENTRY!")
                handle_entry_request(client)
            elif status == "FREE" and "EXIT" in spot_id.upper():
                print("Vehicle at EXIT!")
                handle_exit_request(client)
    
    except Exception as e:
        print(f"Error: {e}")

def handle_entry_request(client):
    global available_spots
    
    print("\n" + "=" * 60)
    print("ENTRY REQUEST")
    print("=" * 60)
    print(f"Available: {available_spots}")
    
    if available_spots > 0:
        print("Opening barrier")
        open_entry_barrier(client)
    else:
        print("PARKING FULL")
    
    print("=" * 60)

def handle_exit_request(client):
    print("\n" + "=" * 60)
    print("EXIT REQUEST")
    print("=" * 60)
    print("Opening exit barrier")
    open_exit_barrier(client)
    print("=" * 60)

def open_entry_barrier(client):
    topic = PREFIX + "parking/barriers/entry/cmd"
    command = {"action": "OPEN"}
    client.publish(topic, json.dumps(command))
    print(f"Command sent: {command}")

def open_exit_barrier(client):
    topic = PREFIX + "parking/barriers/exit/cmd"
    command = {"action": "OPEN"}
    client.publish(topic, json.dumps(command))
    print(f"Command sent: {command}")

def main():
    print("=" * 60)
    print("SMART PARKING - PERSON 2")
    print("=" * 60)
    
    client = mqtt.Client(CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print(f"Connecting to {BROKER}...")
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        client.disconnect()
        print("Goodbye!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()