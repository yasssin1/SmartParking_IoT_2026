# Smart Parking IoT 2026 - Infrastructure MQTT

Ce dépôt contient l'infrastructure de communication pour le projet de parking intelligent. En tant que responsable de la communication (Personne 5), j'ai mis en place ce cadre pour assurer une interopérabilité totale entre nos différents modules.

##  Informations de Connexion au Broker
Tous les modules doivent utiliser les paramètres suivants pour se connecter au réseau :
* **Adresse du Broker :** `broker.emqx.io` 
* **Port :** `1883` 
* **Préfixe obligatoire pour chaque topic :** `smart_parking_2026/` 

##  Vos Identifiants (ClientID)
Pour éviter les déconnexions en boucle, chaque membre de l'équipe **doit** utiliser son ClientID spécifique dans son code:
* **Personne 1 (Capteurs) :** `SmartPark2026_P1` 
* **Personne 2 (Logique) :** `SmartPark2026_P2` 
* **Personne 3 (Barrière) :** `SmartPark2026_P3` 
* **Personne 4 (Afficheur) :** `SmartPark2026_P4` 
* **Personne 5 (Com & Monitoring) :** `SmartPark2026_P5` 
* **Personne 6 (Backend & API) :** `SmartPark2026_P6` 
* **Personne 7 (Dashboard IoT) :** `SmartPark2026_P7` 

##  Table des Topics et Formats JSON
Voici la "partition" que chaque module doit suivre. Les `...` dans les topics doivent être remplacés par le préfixe `smart_parking_2026/`.

| Responsable | Action | Topic MQTT | Format du Message (JSON) |
| :--- | :--- | :--- | :--- |
| **P1** | Publie | `.../parking/spots/{id}/status` | `{"id": "A01", "status": "FREE", "distance_cm": 32.4, "threshold_cm": 50.0, "debounce_n": 4, 
"ts": "2026-01-29T18:25:30"}`  |
| **P2** | S'abonne | `.../parking/spots/+/status` | *(Détection d'arrivée de véhicule)*  |
| **P2** | S'abonne | `.../parking/display/available` | *(Vérification des places libres)*  |
| **P2** | Publie | `.../parking/barriers/entry/cmd` | `{"action": "OPEN"}`  |
| **P3** | S'abonne | `.../parking/barriers/entry/cmd` | *(Attente d'ordre d'ouverture)*  |
| **P3** | Publie | `.../parking/barriers/entry/state` | `{"state": "OPENED"}`  |
| **P4** | S'abonne | `.../parking/spots/+/status` | *(Écoute P1 pour calcul interne)*  |
| **P4** | Publie | `.../parking/display/available` | `{"count": 12}`  |
| **P6** | S'abonne | `.../parking/#` | *(Historisation globale)* [cite: 14] |
| **P6** | Publie | `.../parking/config/new_spot` | `{"id": "B1", "cmd": "ADD"}`  |
| **P7** | S'abonne | `.../parking/#` | *(Visualisation en temps réel)*  |
| **P7** | Publie | `.../parking/admin/override` | `{"cmd": "FORCE_OPEN"}`  |

##  Instructions pour l'équipe
1.  Téléchargez le fichier `client_template.py`.
2.  Changez la variable `CLIENT_ID` à la ligne 9 avec l'identifiant qui vous a été attribué ci-dessus.
3.  Adaptez la section `ABONNEMENTS` et la `LOGIQUE D'ENVOI` selon votre rôle dans la table.
4.  Utilisez toujours `json.dumps()` pour vos publications afin de garantir un format JSON valide.
