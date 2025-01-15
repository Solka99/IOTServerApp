from time import sleep
from main import user_name
import paho.mqtt.client as mqtt
import json

#to działa do publikowania


# Konfiguracja MQTT
BROKER_URL = "192.168.5.242"   # adres ip komputera Gabi połączonego z wifi
BROKER_PORT = 1883
USERNAME = "aaa"
# USERNAME = user_name
PASSWORD = "user1"
# TOPIC = "user1/device1/config"  # Temat, na którym płytka subskrybuje
TOPIC = "username"

# Konfiguracja klienta MQTT
def publish_to_device(data):
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER_URL, BROKER_PORT, 60)

    try:
        # Publikuj dane w formacie JSON
        payload = data
        # payload = json.dumps(data)
        client.publish(TOPIC, payload)
        print(f"Published to {TOPIC}: {payload}")
    except Exception as e:
        print(f"Error publishing to MQTT: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    # Przykładowe dane do wysłania
    config_data = {
        "frequency": 10,  # Co ile sekund płytka ma przesyłać dane
        "temperature_threshold": {
            "min": 20,
            "max": 30
        }
    }
    config_data2={
        "username": USERNAME
    }

    while True:
        if USERNAME != '':
            # publish_to_device(config_data2)
            publish_to_device(USERNAME)
            sleep(5)
