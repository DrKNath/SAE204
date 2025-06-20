#!/usr/bin/env python3
# Fichier: mqtt_to_mariadb.py

import paho.mqtt.client as mqtt
import pymysql
import json
from datetime import datetime
import sys

# Configuration MQTT
BROKER_HOST = "test.mosquitto.org"
BROKER_PORT = 1883
TOPICS = [
    "IUT/Colmar2025/SAE2.04/Maison1",
    "IUT/Colmar2025/SAE2.04/Maison2"
]

# Configuration MariaDB - MODIFIEZ CES VALEURS
DB_CONFIG = {
    'host': 'localhost',  # ou l'IP de votre serveur MariaDB
    'port': 3306,
    'user': 'votre_utilisateur',  # remplacez par votre utilisateur
    'password': 'votre_mot_de_passe',  # remplacez par votre mot de passe
    'database': 'votre_base_de_donnees',  # remplacez par le nom de votre BDD
    'charset': 'utf8mb4'
}

# Nom de votre table - MODIFIEZ selon votre structure
TABLE_NAME = 'capteurs_iot'  # remplacez par le nom de votre table

def test_database_connection():
    """Teste la connexion à la base de données"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        print("✓ Connexion à MariaDB réussie")
        return True
    except Exception as e:
        print(f"✗ Erreur de connexion à MariaDB: {e}")
        return False

def parse_message(message):
    """Parse le message au format: Id=12A6B8AF6CD3,piece=sejour,date=15/06/2022,heure=12:13:14,temp=26,35"""
    try:
        data = {}
        pairs = message.split(',')
        for pair in pairs:
            key, value = pair.split('=', 1)
            data[key] = value
        return data
    except Exception as e:
        print(f"Erreur lors du parsing: {e}")
        return {}

def save_to_mariadb(topic, message, parsed_data):
    """Sauvegarde en base de données MariaDB"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        timestamp = datetime.now()
        
        # ADAPTEZ CETTE REQUÊTE À VOTRE STRUCTURE DE TABLE
        # Exemple avec colonnes: id(auto), timestamp, topic, device_id, piece, date_capteur, heure_capteur, temperature, raw_message
        query = f"""
            INSERT INTO {TABLE_NAME} 
            (timestamp, topic, device_id, piece, date_capteur, heure_capteur, temperature, raw_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            timestamp,
            topic,
            parsed_data.get('Id', ''),
            parsed_data.get('piece', ''),
            parsed_data.get('date', ''),
            parsed_data.get('heure', ''),
            float(parsed_data.get('temp', 0)) if parsed_data.get('temp') else None,
            message
        )
        
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        connection.close()
        print(f"✓ Données sauvegardées en BDD")
        
    except Exception as e:
        print(f"✗ Erreur lors de la sauvegarde: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connecté au broker MQTT {BROKER_HOST}")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"Abonné au topic: {topic}")
    else:
        print(f"Échec de connexion MQTT, code: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    message = msg.payload.decode('utf-8')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Parse du message
    parsed_data = parse_message(message)
    
    # Affichage console
    print(f"\n[{timestamp}] Topic: {topic}")
    print(f"Message: {message}")
    if parsed_data:
        print(f"ID: {parsed_data.get('Id', 'N/A')}")
        print(f"Pièce: {parsed_data.get('piece', 'N/A')}")
        print(f"Date: {parsed_data.get('date', 'N/A')}")
        print(f"Heure: {parsed_data.get('heure', 'N/A')}")
        print(f"Température: {parsed_data.get('temp', 'N/A')}°C")
    print("-" * 50)
    
    # Sauvegarde en BDD MariaDB
    save_to_mariadb(topic, message, parsed_data)

def main():
    print("=== Client MQTT vers MariaDB ===")
    
    # Test de la connexion à la base de données
    if not test_database_connection():
        print("Vérifiez votre configuration de base de données dans le script")
        sys.exit(1)
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        print("Appuyez sur Ctrl+C pour arrêter")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nArrêt du client MQTT")
        client.disconnect()
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    main()