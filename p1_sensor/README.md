Personne 1 – Capteurs de présence (Simulation)

Ce module implémente la simulation des capteurs de présence du projet
Smart Parking IoT 2026.

Il comprend :

des capteurs de places de parking (type ultrason)

des capteurs de passage à l’entrée et à la sortie du parking

Chaque capteur publie son état via MQTT, uniquement lorsqu’un changement est détecté.

🎯 Rôle du module

Simuler des capteurs de présence pour 20 places de parking

Simuler des capteurs de passage à l’entrée et à la sortie

Appliquer une logique réaliste :

mesure de distance

seuil de détection

mécanisme de stabilisation (debounce)

Publier les événements et états via MQTT

Ce module constitue la source de vérité pour :

l’occupation des places

la détection d’entrée et de sortie des véhicules

🅿️ Places simulées

Nombre de places : 20

Identifiants :
A01, A02, A03, … , A20

Chaque place fonctionne de manière indépendante.

📏 Logique de détection (places)

Une distance est simulée pour chaque place :

Place libre : 150–280 cm

Place occupée : 10–35 cm

Un bruit léger est ajouté pour simuler un capteur réel.

Seuil de détection

THRESHOLD = 50 cm

distance < 50 cm → OCCUPIED

distance ≥ 50 cm → FREE

🔁 Debounce (anti-clignotement)

Pour éviter les changements erratiques dus au bruit :

un changement d’état est validé uniquement après
4 lectures consécutives identiques (DEBOUNCE_N = 4)

la logique de debounce est interne à chaque capteur

🚧 Capteurs d’entrée et de sortie (ENTRY / EXIT)

En plus des places, le module simule :

un capteur d’entrée

un capteur de sortie

Ces capteurs représentent des capteurs de passage (barrière, faisceau IR).

Comportement

État par défaut : FREE

Lorsqu’un véhicule passe :

le capteur devient OCCUPIED pendant 1.5 à 3 secondes

puis revient automatiquement à FREE

Les événements sont publiés uniquement lors d’un changement d’état

Ces capteurs sont indépendants des places et servent à détecter :

une entrée de véhicule

une sortie de véhicule

📡 Communication MQTT
Connexion au broker

Broker : broker.emqx.io

Port : 1883

ClientID : SmartPark2026_P1

Préfixe obligatoire des topics :
smart_parking_2026/

📤 Topics publiés
Capteurs de places
smart_parking_2026/parking/spots/{id}/status


Exemple :

smart_parking_2026/parking/spots/A06/status

Capteur d’entrée
smart_parking_2026/parking/entry_sensor/status

Capteur de sortie
smart_parking_2026/parking/exit_sensor/status

🧾 Format des messages publiés (JSON)
Place de parking
{
  "id": "A06",
  "status": "OCCUPIED",
  "distance_cm": 19.8,
  "threshold_cm": 50.0,
  "debounce_n": 4,
  "ts": "2026-02-03T02:09:10"
}

Capteur ENTRY / EXIT
{
  "status": "OCCUPIED",
  "ts": "2026-02-03T02:08:26"
}

📌 Publication

Les messages sont publiés :

uniquement lors d’un changement d’état

avec l’option retain = true

▶️ Exécution
Installation des dépendances
pip install paho-mqtt

Lancement du module
python p1_sensor/sensor_p1.py

🧪 Tests
▶️ Test A — Local

Démarrer Mosquitto :

mosquitto -v


Modifier temporairement dans le code :

BROKER_HOST = "127.0.0.1"


S’abonner aux topics :

mosquitto_sub -h 127.0.0.1 -t "smart_parking_2026/parking/#" -v


Lancer le script :

python p1_sensor/sensor_p1.py

▶️ Test B — Intégration (broker public)

Conserver :

BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883


S’abonner :

mosquitto_sub -h broker.emqx.io -p 1883 -t "smart_parking_2026/parking/#" -v


Lancer le script :

python p1_sensor/sensor_p1.py