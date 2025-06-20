#!/usr/bin/env python3
# Fichier: mqtt_to_file.py

import paho.mqtt.client as mqtt
import json
from datetime import datetime
import os

# Configuration
BROKER_HOST = "test.mosquitto.org"
BROKER_PORT = 1883
TOPICS = [
    "IUT/Colmar2025/SAE2.04/Maison1",
    "IUT/Colmar2025/SAE2.04/Maison2"
]
LOG_FILE = "mqtt_messages.txt"

def parse_message(message):
    """Parse le message au format: Id=12A6B8AF6CD3,piece=sejour,date=15/06/2022,heure=12:13:14,temp=26,35"""
    try:
        data = {}
        pairs = message.split(',')
        for pair in pairs:
            key, value = pair.split('=', 1)
            data[key] = value
        return data
    except:
        return {"raw_message": message}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connecté au broker MQTT {BROKER_HOST}")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"Abonné au topic: {topic}")
    else:
        print(f"Échec de connexion, code: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode('utf-8')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Parse du message
    parsed_data = parse_message(message)
    
    # Affichage console
    print(f"[{timestamp}] Topic: {topic}")
    print(f"Message: {message}")
    print(f"Données parsées: {parsed_data}")
    print("-" * 50)
    
    # Sauvegarde dans fichier
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] Topic: {topic}\n")
        f.write(f"Message: {message}\n")
        f.write(f"Données: {json.dumps(parsed_data, ensure_ascii=False)}\n")
        f.write("-" * 50 + "\n")

def main():
    # Créer le fichier de log s'il n'existe pas
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== Log MQTT démarré le {datetime.now()} ===\n")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        print(f"Sauvegarde des messages dans: {LOG_FILE}")
        print("Appuyez sur Ctrl+C pour arrêter")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nArrêt du client MQTT")
        client.disconnect()
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    main()