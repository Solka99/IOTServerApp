from time import sleep
# from main import user_name, read_send_times_from_db_and_transform_to_string
from models import SendTimes, SensorData, User
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
TOPIC_USERNAME = "username"
TOPIC_SENDING_TIMES ="sending_times"

data_from_beacon={
    "username":'aaa',
    "mac_address":''
}

def send_times_to_beacon():
    # Pobierz czasy z bazy danych i sformatuj jako listę HH:MM
    send_times = [t.strftime('%H:%M') for t in read_send_times_from_db_and_transform_to_string()]
    # Utwórz dane do wysyłki
    payload = json.dumps({"send_times": send_times})

    # Publikuj dane do urządzenia
    publish_to_device(payload,TOPIC_SENDING_TIMES)

def send_limits_to_beacon():
    # Pobierz czasy z bazy danych i sformatuj jako listę HH:MM
    send_times = [t.strftime('%H:%M') for t in read_send_times_from_db_and_transform_to_string()]
    # Utwórz dane do wysyłki
    payload = json.dumps({"send_times": send_times})

    # Publikuj dane do urządzenia
    publish_to_device(payload,TOPIC_SENDING_TIMES)


def read_send_times_from_db_and_transform_to_string():
    username = data_from_beacon.get('username')
    user_id = User.query.filter_by(username=username).first().id
    if user_id:
        lst=SendTimes.query.filter_by(variables_id=user_id).all()
        send_times = [st.send_time for st in lst]
        return send_times
    else:
        print('Nie ma takiego użytkownika!')
# def read_changed_limits_from_db():
#     """lista będzie się składać z obu limitów, niezależnie od tego czy użytkownik zmienił oba"""
#     user_id = data_from_beacon.get('username')
#     if user_id:
#         lst=SensorData.query.filter_by(variables_id=user_id).all()
#         send_times = [st.send_time for st in lst]
#         return send_times
#     else:
#         print('Nie ma takiego użytkownika!')
# Konfiguracja klienta MQTT
def publish_to_device(data,topic):
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER_URL, BROKER_PORT, 60)

    try:
        # Publikuj dane w formacie JSON
        payload = data
        # payload = json.dumps(data)
        client.publish(topic, payload)
        print(f"Published to {topic}: {payload}")
    except Exception as e:
        print(f"Error publishing to MQTT: {e}")
    finally:
        client.disconnect()

def publish_to_device_2(data1,topic):
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER_URL, BROKER_PORT, 60)

    try:
        # Publikuj dane w formacie JSON
        a=data1[0]
        b=data1[1]
        data = str(a)+' '+str(b)
        payload = data
        # payload = json.dumps(data)
        client.publish(topic, payload)
        print(f"Published to {topic}: {payload}")
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

    # send_to_beacon()
    # while True:
    #     if USERNAME != '':
    #         # publish_to_device(config_data2, TOPIC
    # publish_to_device(USERNAME, TOPIC_USERNAME)
    #         # send_to_beacon()
    #         sleep(5)
