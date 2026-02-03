import time, json, random
from datetime import datetime
import paho.mqtt.client as mqtt

# =========================
# Part A — Configuration
# =========================

BROKER_HOST = "broker.emqx.io"  # public MQTT broker for testing ("127.0.0.1" for localhost testing)
BROKER_PORT = 1883             # default MQTT port

# 20 parking spots: A01..A20
SPOTS = [f"A{i:02d}" for i in range(1, 21)]

THRESHOLD_CM = 50.0   # distance below which a spot is considered OCCUPIED
READ_INTERVAL_S = 1.0 # loop frequency (1 reading per second)
DEBOUNCE_N = 4        # number of consistent readings to confirm status change (anti-flicker)

# Ultrasonic-like distance simulation ranges
DIST_FREE = (150, 280)  # cm when no car (sensor sees the floor)
DIST_PARK = (10, 35)    # cm when car is present (sensor sees the car)
NOISE_CM = 2.0          # small noise to imitate real sensor variation

# Entry/Exit sensors topics (gate sensors, not parking spots)
ENTRY_TOPIC = "smart_parking_2026/parking/entry_sensor/status"
EXIT_TOPIC  = "smart_parking_2026/parking/exit_sensor/status"

# Timing for entry/exit sensor behavior:
# - When triggered, it becomes OCCUPIED for a short time (car passing)
# - Then it returns to FREE automatically
ENTRY_EXIT_OCCUPIED_SECONDS = (1.5, 3.0)  # how long ENTRY/EXIT stays OCCUPIED when a car passes
ENTRY_EXIT_FREE_SECONDS = (4.0, 12.0)     # time between triggers (demo-friendly)

def now():
    return datetime.now().isoformat(timespec="seconds")

# =========================
# Part B — Parking Spot Sensor Simulation
# =========================
class Spot:
    def __init__(self, spot_id: str):
        self.spot_id = spot_id
        self.has_car = False  # internally the spot starts empty
        self.activity = random.uniform(0.6, 1.6)  # higher = changes more often
        self.next_switch = time.time() + self._free_duration()  # when car arrives/leaves next

        self.stable_status = "FREE"  # the final stable status (after debounce)
        self.occ_count = 0
        self.free_count = 0

    def _park_duration(self):
        base = random.uniform(45, 180)  # seconds parked
        return base / self.activity

    def _free_duration(self):
        base = random.uniform(30, 150)  # seconds free
        return base / self.activity

    def _update_world(self):
        # Simulate car arrival/leave after some time
        t = time.time()
        if t >= self.next_switch:
            self.has_car = not self.has_car
            self.next_switch = t + (self._park_duration() if self.has_car else self._free_duration())

    def read_distance(self) -> float:
        # Simulate ultrasonic sensor distance
        self._update_world()

        # if there is a car, distance is small else large
        base = random.uniform(*(DIST_PARK if self.has_car else DIST_FREE))

        # add noise (real sensors fluctuate)
        noise = random.uniform(-NOISE_CM, NOISE_CM)

        return max(0.0, base + noise)

    def update_debounced_status(self, distance_cm: float) -> str:
        # Convert distance to instant detection
        detected_occ = distance_cm < THRESHOLD_CM

        # Count consecutive detections (anti-flicker)
        if detected_occ:
            self.occ_count += 1
            self.free_count = 0
        else:
            self.free_count += 1
            self.occ_count = 0

        # Switch only if enough confirmations
        if self.stable_status != "OCCUPIED" and self.occ_count >= DEBOUNCE_N:
            self.stable_status = "OCCUPIED"
            self.occ_count = 0
            self.free_count = 0

        elif self.stable_status != "FREE" and self.free_count >= DEBOUNCE_N:
            self.stable_status = "FREE"
            self.occ_count = 0
            self.free_count = 0

        return self.stable_status

# =========================
# Part B.2 — Gate Sensor (ENTRY / EXIT)
# =========================
class GateSensor:
    """
    Gate sensors are event sensors:
    - Usually FREE
    - Become OCCUPIED briefly when a car passes
    - Return to FREE automatically
    """
    def __init__(self, name: str, topic: str):
        self.name = name
        self.topic = topic
        self.state = "FREE"
        # Initial delay before the first car passes
        self.next_toggle = time.time() + random.uniform(*ENTRY_EXIT_FREE_SECONDS)

    def step(self) -> str:
        t = time.time()
        if t >= self.next_toggle:
            if self.state == "FREE":
                # A car is passing the gate
                self.state = "OCCUPIED"
                self.next_toggle = t + random.uniform(*ENTRY_EXIT_OCCUPIED_SECONDS)
            else:
                # The car has passed, gate becomes free again
                self.state = "FREE"
                self.next_toggle = t + random.uniform(*ENTRY_EXIT_FREE_SECONDS)
        return self.state
# =========================
# Part C — Main loop : publish to MQTT only on change
# =========================
def main():
    # 1) Connect to MQTT broker
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="SmartPark2026_P1"
    )
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()

    # 2) Create sensors
    spots = [Spot(s) for s in SPOTS]

    # KeyError-proof: build dict from actual spot objects
    last_published_spots = {sp.spot_id: None for sp in spots}

    entry_sensor = GateSensor("ENTRY", ENTRY_TOPIC)
    exit_sensor  = GateSensor("EXIT", EXIT_TOPIC)
    last_entry_state = None
    last_exit_state = None

    print("20 spots (A01..A20) + ENTRY/EXIT sensors started. Publishing only on change...")

    try:
        while True:
            # ---- Parking spots ----
            for sp in spots:
                d = sp.read_distance()
                status = sp.update_debounced_status(d)

                # KeyError-proof access with .get()
                if status != last_published_spots.get(sp.spot_id):
                    last_published_spots[sp.spot_id] = status

                    topic = f"smart_parking_2026/parking/spots/{sp.spot_id}/status"
                    payload = {
                        "id": sp.spot_id,
                        "status": status,
                        "distance_cm": round(d, 1),
                        "threshold_cm": THRESHOLD_CM,
                        "debounce_n": DEBOUNCE_N,
                        "ts": now()
                    }
                    client.publish(topic, json.dumps(payload), qos=1, retain=True)
                    print(f"{payload['ts']} | {sp.spot_id} => {status} (distance={payload['distance_cm']}cm)")

            # ---- Entry sensor ----
            entry_state = entry_sensor.step()
            if entry_state != last_entry_state:
                last_entry_state = entry_state
                payload = {"status": entry_state, "ts": now()}
                client.publish(ENTRY_TOPIC, json.dumps(payload), qos=1, retain=True)
                print(f"{payload['ts']} | ENTRY_SENSOR => {entry_state}")

            # ---- Exit sensor ----
            exit_state = exit_sensor.step()
            if exit_state != last_exit_state:
                last_exit_state = exit_state
                payload = {"status": exit_state, "ts": now()}
                client.publish(EXIT_TOPIC, json.dumps(payload), qos=1, retain=True)
                print(f"{payload['ts']} | EXIT_SENSOR => {exit_state}")

            time.sleep(READ_INTERVAL_S)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()