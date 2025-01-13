import paho.mqtt.client as mqtt
import json

# Konfiguracja MQTT
BROKER_URL = "127.0.0.1"
BROKER_PORT = 1883
USERNAME = "user1"
PASSWORD = "user1"
TOPIC = "user1/device1/config"  # Temat, na którym płytka subskrybuje

# Konfiguracja klienta MQTT
def publish_to_device(data):
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER_URL, BROKER_PORT, 60)

    try:
        # Publikuj dane w formacie JSON
        payload = json.dumps(data)
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

    publish_to_device(config_data)
