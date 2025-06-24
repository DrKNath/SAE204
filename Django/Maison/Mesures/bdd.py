import paho.mqtt.client as mqtt
import pymysql
from datetime import datetime
import re
import logging
import threading

# Configuration de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration MQTT (à personnaliser)
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "IUT/Colmar2025/SAE2.04/Maison1"
MQTT_USERNAME = None
MQTT_PASSWORD = None

# Configuration Base de données (à personnaliser)
DB_CONFIG = {
    'host': '10.252.7.132',
    'user': 'bdd',
    'password': 'toto',
    'database': 'Maison',
    'charset': 'utf8mb4',
    'autocommit': True
}

class MQTTToDatabaseProcessor:
    def __init__(self, db_config, mqtt_config):
        self.db_config = db_config
        self.mqtt_config = mqtt_config
        self.db_connection = None
        self.mqtt_client = None

    def connect_to_database(self):
        try:
            self.db_connection = pymysql.connect(**self.db_config)
            logger.info("Connexion à la base de données établie")
            return True
        except pymysql.Error as err:
            logger.error(f"Erreur de connexion à la base de données: {err}")
            return False

    def parse_mqtt_message(self, message):
        try:
            clean_message = re.sub(r'\s+', ' ', message.strip())
            patterns = {
                'id': r'Id=([^,]+)',
                'piece': r'piece=([^,]+)',
                'date': r'date=\s*([^,]+)',
                'time': r'time=([^,]+)',
                'temp': r'temp=([^,\s]+)'
            }
            data = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, clean_message)
                if match:
                    data[key] = match.group(1).strip()
                else:
                    logger.warning(f"Champ {key} non trouvé dans le message: {clean_message}")
                    return None

            # Conversion de la date et heure
            date_str = data['date'].strip()
            time_str = data['time'].strip()
            datetime_str = f"{date_str} {time_str}"
            timestamp = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M:%S")
            temperature = float(data['temp'])
            return {
                'id_capteur': data['id'],
                'piece': data['piece'],
                'timestamp': timestamp,
                'temperature': temperature
            }
        except Exception as e:
            logger.error(f"Erreur lors du parsing du message: {e}")
            return None

    def insert_or_update_capteur(self, capteur_data):
        try:
            cursor = self.db_connection.cursor()
            check_query = "SELECT id_capteur FROM capteur WHERE id_capteur = %s"
            cursor.execute(check_query, (capteur_data['id_capteur'],))
            if cursor.fetchone() is None:
                insert_query = """
                INSERT INTO capteur (id_capteur, nom_capteur, piece, emplacement)
                VALUES (%s, %s, %s, %s)
                """
                nom_capteur = f"Capteur_{capteur_data['piece']}_{capteur_data['id_capteur'][-6:]}"
                emplacement = f"Capteur situé en {capteur_data['piece']}"
                cursor.execute(insert_query, (
                    capteur_data['id_capteur'],
                    nom_capteur,
                    capteur_data['piece'],
                    emplacement
                ))
                logger.info(f"Nouveau capteur ajouté: {capteur_data['id_capteur']}")
            else:
                update_query = "UPDATE capteur SET piece = %s WHERE id_capteur = %s"
                cursor.execute(update_query, (capteur_data['piece'], capteur_data['id_capteur']))
            cursor.close()
            return True
        except pymysql.Error as err:
            logger.error(f"Erreur lors de l'insertion/mise à jour du capteur: {err}")
            return False

    def insert_mesure(self, mesure_data):
        try:
            cursor = self.db_connection.cursor()
            insert_query = """
            INSERT INTO mesures (id_capteur, timestamp, temperature)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (
                mesure_data['id_capteur'],
                mesure_data['timestamp'],
                mesure_data['temperature']
            ))
            cursor.close()
            logger.info(f"Mesure ajoutée pour capteur {mesure_data['id_capteur']}: {mesure_data['temperature']}°C")
            return True
        except pymysql.Error as err:
            logger.error(f"Erreur lors de l'insertion de la mesure: {err}")
            return False

    def process_mqtt_data(self, parsed_data):
        try:
            if not self.insert_or_update_capteur(parsed_data):
                return False
            if not self.insert_mesure(parsed_data):
                return False
            self.db_connection.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors du traitement des données: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connexion au broker MQTT réussie")
            client.subscribe(self.mqtt_config['topic'])
            logger.info(f"Abonnement au topic: {self.mqtt_config['topic']}")
        else:
            logger.error(f"Échec de connexion au broker MQTT, code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            message = msg.payload.decode('utf-8')
            logger.info(f"Message reçu: {message}")
            parsed_data = self.parse_mqtt_message(message)
            if parsed_data is None:
                logger.warning("Impossible de parser le message")
                return
            if self.process_mqtt_data(parsed_data):
                logger.info("Données traitées avec succès")
            else:
                logger.error("Échec du traitement des données")
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message MQTT: {e}")

    def on_disconnect(self, client, userdata, rc):
        logger.info("Déconnexion du broker MQTT")

    def start(self):
        if not self.connect_to_database():
            return False
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        if self.mqtt_config.get('username') and self.mqtt_config.get('password'):
            self.mqtt_client.username_pw_set(
                self.mqtt_config['username'],
                self.mqtt_config['password']
            )
        try:
            self.mqtt_client.connect(
                self.mqtt_config['broker'],
                self.mqtt_config['port'],
                60
            )
            logger.info("Démarrage de la collecte de données...")
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
            self.stop()
        except Exception as e:
            logger.error(f"Erreur lors du démarrage: {e}")
            return False

    def stop(self):
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            self.mqtt_client.loop_stop()
        if self.db_connection:
            self.db_connection.close()
        logger.info("Processus arrêté")
