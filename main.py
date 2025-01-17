from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
from datetime import datetime
from flask import flash
import json
from models import db, User, IoTDevice, UserDefinedVariables, SendTimes, SensorData
import os
from mqtt_publish import *


# Dane do wysłania
# mosquitto_pub -h 127.0.0.1 -p 1883 -t "user1/device1/temperature" -m '{\"value\": 25.5}'



app = Flask(__name__)
app.secret_key = 'abc'

# Konfiguracja bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iot_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicjalizacja bazy danych
db.init_app(app)


mac_global=''
# MQTT konfiguracja
BROKER_URL = "192.168.5.242"
BROKER_PORT = 1883

USERNAME = "user1"
PASSWORD = "user1"

TOPICS = [
    "user1/+/temperature",
    # "user1/+/humidity",
    "+/+/temperature",
    "+/+/readings"
]

# 'username'/'adres::mac'/'
user_name=''

# Modele bazy danych
class SensorData2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

def save_data_to_db(topic, value):
    with app.app_context():  # Wymuszenie kontekstu aplikacji
        try:
            timestamp = datetime.now()
            # Konwersja wartości na ciąg znaków JSON
            print(value)
            value_str = json.dumps(value)  # Zamienia słownik na JSON w formie tekstu
            topic_parts = topic.split('/')
            topic_parts.pop()
            new_data_good = SensorData(device_id= topic_parts[1], temperature=value['temperature'], pressure=value['pressure'],timestamp=timestamp )
            # new_data = SensorData2(topic=topic, value=value_str, timestamp=timestamp)
            # db.session.add(new_data)
            # db.session.commit()
            db.session.add(new_data_good)
            db.session.commit()
            print(f"Saved to DB: {topic} -> {value_str} at {timestamp}")
        except Exception as e:
            print(f"Error saving to database: {e}")


# def send_to_beacon():
#     # read_send_times_from_db_and_transform_to_string()
#     a = read_send_times_from_db_and_transform_to_string()
#
#     data = {
#         "send_times": a
#     }
#     # Konwersja datetime.time na czytelny format, np. HH:MM
#     data_serializable = {
#         'send_times': [t.strftime('%H:%M') for t in data['send_times']]
#     }
#     payload = json.dumps(data_serializable)
#     publish_to_device(payload)



# Callback: Po połączeniu z brokerem
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
    else:
        print(f"Failed to connect, return code {rc}")

# Callback: Po odebraniu wiadomości
def on_message(client, userdata, msg):
    try:
        value = json.loads(msg.payload.decode("utf-8"))
        print(f"Received: {value} on topic: {msg.topic}")
        save_data_to_db(msg.topic, value)
    except Exception as e:
        print(f"Error processing message: {e}")


# Konfiguracja klienta MQTT
def setup_mqtt():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_URL, BROKER_PORT, 60)
    client.loop_start()  # Uruchom klienta MQTT w osobnym wątku


def read_username_from_db():
    user_id = session['user_id']
    global user_name
    user_name = User.query.get(user_id).username


@app.route('/', defaults={'mac_address': None}, methods=['GET'])
@app.route('/<mac_address>', methods=['GET'])
def home(mac_address):
    global mac_global
    mac_global=mac_address
    # # read_send_times_from_db_and_transform_to_string()
    # a = read_send_times_from_db_and_transform_to_string()
    #
    # data = {
    #     "send_times": a
    # }
    # # Konwersja datetime.time na czytelny format, np. HH:MM
    # data_serializable = {
    #     'send_times': [t.strftime('%H:%M') for t in data['send_times']]
    # }
    # payload = json.dumps(data_serializable)
    # publish_to_device(payload)
    return render_template('index.html',mac_address=mac_address)

# @app.route('/register', defaults={'mac_address': None}, methods=['POST'])
# @app.route('/register/<mac_address>', methods=['POST'])
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists!'}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully!'}), 201

# @app.route('/login', defaults={'mac_address': None}, methods=['POST'])
# @app.route('/login/<mac_address>', methods=['POST'])
@app.route('/login', methods=['POST'])
def login():
    mac_address=mac_global
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'error': 'Invalid username or password!'}), 401

    session['user_id'] = user.id

    # Rejestracja nowego urządzenia, jeśli podano mac_address
    if mac_address:
        existing_device = IoTDevice.query.filter_by(device_id=mac_address).first()
        if existing_device:
            return jsonify({'error': f'Device {mac_address} is already registered!'}), 400

        new_device = IoTDevice(
            device_id=mac_address,
            name='new',
            owner_id=user.id,
            registered_at=datetime.now()
        )
        db.session.add(new_device)
        db.session.commit()

        publish_to_device(user.username,'username')
        # # flash(f'Device {mac_address} has been registered successfully!', 'success')\
        # session['message'] = f'Device {mac_address} has been registered successfully!'
        flash(f'Device {mac_address} has been registered successfully!', 'success')
        print(f'Device {mac_address} has been registered successfully!')
        return redirect(url_for('dashboard'))
        # return jsonify({'redirect': url_for('dashboard')}), 200

    return jsonify({'redirect': url_for('dashboard')}), 200
    # return jsonify({'message': f'Welcome, {user.username}!'}), 200



@app.route('/set_parameters', methods=['GET', 'POST'])
def set_parameters():
    """Obsługuje pobieranie i aktualizację wszystkich parametrów."""
    if 'user_id' not in session:
        return redirect(url_for('home'))  # Jeśli nie ma sesji, przekieruj na stronę główną

    user_id = session['user_id']
    user_variables = UserDefinedVariables.query.filter_by(user_id=user_id).first()

    if request.method == 'POST':
        # Pobierz dane z formularza
        lower_temp_limit = request.form.get('lower_temp_limit')
        higher_temp_limit = request.form.get('higher_temp_limit')
        frequency = request.form.get('frequency')

        if int(frequency) < 1 or int(frequency) > 24:
            return render_template(
                            'set_parameters.html',
                            lower_temp_limit=lower_temp_limit,
                            higher_temp_limit=higher_temp_limit,
                            frequency=frequency,
                            error=f"Invalid value: '{frequency}'.It should be between 1 and 24."
                        )
        # send_times = request.form.get('send_times')

        # # Walidacja godzin (send_times)
        # valid_times = []
        # if send_times:
        #     for time_str in send_times.split(','):
        #         time_str = time_str.strip()
        #         try:
        #             # Konwersja na obiekt czasu
        #             time_obj = datetime.strptime(time_str, '%H:%M').time()
        #             valid_times.append(time_obj)
        #         except ValueError:
        #             # Jeśli format jest nieprawidłowy
        #             return render_template(
        #                 'set_parameters.html',
        #                 lower_temp_limit=lower_temp_limit,
        #                 higher_temp_limit=higher_temp_limit,
        #                 send_times=send_times,
        #                 error=f"Invalid time format: '{time_str}'. Use HH:MM format."
        #             )

        # Jeśli brak zmiennych użytkownika, utwórz je
        if not user_variables:
            user_variables = UserDefinedVariables(user_id=user_id)
            db.session.add(user_variables)

        # Zapisz nowe wartości
        user_variables.lower_temp_limit = int(lower_temp_limit) if lower_temp_limit else None
        user_variables.higher_temp_limit = int(higher_temp_limit) if higher_temp_limit else None
        user_variables.frequency = int(frequency) if frequency else None

        # # Aktualizuj godziny wysyłania
        # SendTimes.query.filter_by(variables_id=user_variables.user_id).delete()  # Usuń poprzednie godziny
        # if send_times:
        #     for time_str in send_times.split(','):
        #         time_obj = datetime.strptime(time_str.strip(), '%H:%M').time()
        #         db.session.add(SendTimes(variables=user_variables, send_time=time_obj))

        db.session.commit()
        flash('Parameters set successfully!', 'success')
        return redirect(url_for('set_parameters'))

    # Przygotuj dane do wyświetlenia w formularzu
    lower_temp_limit = user_variables.lower_temp_limit if user_variables else ''
    higher_temp_limit = user_variables.higher_temp_limit if user_variables else ''
    frequency = user_variables.frequency if user_variables else ''
    # send_times = (
    #     ', '.join([time.send_time.strftime('%H:%M') for time in user_variables.send_times])
    #     if user_variables and user_variables.send_times
    #     else ''
    # )

    return render_template(
        'set_parameters.html',
        lower_temp_limit=lower_temp_limit,
        higher_temp_limit=higher_temp_limit,
        # send_times=send_times
        frequency=frequency,
    )

@app.route('/mqtt_send', methods=['POST'])
def mqtt_send():
    # save_data_to_db()
    publish_to_device(read_frequency_from_db(), 'sending_times')
    publish_to_device_2(read_changed_limits_from_db(), 'limits')

    return jsonify({'message': f'Updated parameters successfully!'}), 201

    # # Zwróć odpowiedź do przeglądarki
    # return "Python function executed successfully!", 200
@app.route('/register_device', methods=['POST'])
def register_device():
    read_username_from_db()

    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access!'}), 403

    user_id = session['user_id']
    data = request.get_json()
    device_id = data.get('device_id')
    device_name = data.get('device_name')

    if not device_id or not device_name:
        return jsonify({'error': 'Device ID and name are required!'}), 400

    # Sprawdź, czy urządzenie już istnieje w bazie
    device = IoTDevice.query.filter_by(device_id=device_id).first()

    if device:
        # Jeśli urządzenie ma już właściciela
        if device.owner_id == user_id:
            return jsonify({'message': 'Device is already registered to your account!'}), 200
        else:
            # Przypisz urządzenie do nowego właściciela
            previous_owner = User.query.get(device.owner_id)
            device.owner_id = user_id
            device.name = device_name
            device.registered_at = datetime.now()
            db.session.commit()
            return jsonify({
                'message': f'Device {device.device_name} is now registered to your account. '
                           f'Previous owner ({previous_owner.username}) has lost access.'
            }), 200
    else:
        # Utwórz nowe urządzenie i przypisz je do użytkownika
        new_device = IoTDevice(
            device_id=device_id,
            name=device_name,
            owner_id=user_id,
            registered_at=datetime.utcnow()
        )
        db.session.add(new_device)
        db.session.commit()
        return jsonify({'message': f'Device {device_id} has been registered successfully!'}), 201

@app.route('/register_device_form', methods=['GET'])
def register_device_form():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('register_device.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Przekierowanie do logowania, jeśli użytkownik nie jest zalogowany

    return render_template('dashboard.html')

@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user_id', None)  # Usuń użytkownika z sesji
    return redirect(url_for('home'))  # Przekierowanie na stronę logowania

@app.route('/device_data', methods=['GET'])
def device_data():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_devices = IoTDevice.query.filter_by(owner_id=user_id).all()

    if not user_devices:
        return render_template('device_data.html', data=[], message="No devices registered.")

    device_ids = [device.device_id.upper() for device in user_devices]
    print(device_ids)
    data = SensorData.query.filter(SensorData.device_id.in_(device_ids)).order_by(SensorData.timestamp.desc()).all()
    print(type(data))
    print(data)
    return render_template('device_data.html', data=data, message=None)

@app.route('/save_sensor_data', methods=['POST'])
def save_sensor_data():
    data = request.get_json()
    device_id = data.get('device_id')
    temperature = data.get('temperature')
    pressure = data.get('pressure')

    # Weryfikacja urządzenia
    device = IoTDevice.query.filter_by(device_id=device_id).first()
    if not device:
        return jsonify({'error': 'Invalid device ID!'}), 400

    # Zapis danych do bazy
    new_data = SensorData(device_id=device_id, temperature=temperature, pressure=pressure)
    db.session.add(new_data)
    db.session.commit()
    return jsonify({'message': 'Data saved successfully!'}), 201

# @app.route('/publish_to_device', methods=['POST'])
# def publish_to_device():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Unauthorized access!'}), 403
#
#     user_id = session['user_id']
#
#     # Pobierz dane użytkownika z bazy danych
#     user_variables = UserDefinedVariables.query.filter_by(user_id=user_id).first()
#     if not user_variables:
#         return jsonify({'error': 'No parameters set for this user!'}), 404
#
#     # Utwórz payload z danymi
#     payload = {
#         "lower_temp_limit": user_variables.lower_temp_limit,
#         "higher_temp_limit": user_variables.higher_temp_limit,
#         "send_times": [time.send_time.strftime('%H:%M') for time in user_variables.send_times]
#     }
#
#     try:
#         # Konfiguracja klienta MQTT
#         client = mqtt.Client()
#         client.username_pw_set(USERNAME, PASSWORD)
#         client.connect(BROKER_URL, BROKER_PORT, 60)
#
#         # Publikacja danych
#         topic = f"user{user_id}/device/config"
#         client.publish(topic, json.dumps(payload))
#         client.disconnect()
#
#         return jsonify({'message': 'Configuration published to device!'}), 200
#     except Exception as e:
#         return jsonify({'error': f'Failed to publish data: {str(e)}'}), 500
def read_frequency_from_db():
    username = data_from_beacon.get('username')
    user_id = User.query.filter_by(username=username).first().id
    if user_id:
        result = UserDefinedVariables.query.filter_by(user_id=user_id).first()
        frequency = result.frequency if result else None
        return frequency
    else:
        print('Nie ma takiego użytkownika!')


def read_changed_limits_from_db():
    """lista będzie się składać z obu limitów, niezależnie od tego czy użytkownik zmienił oba"""
    username = data_from_beacon.get('username')
    user_id = User.query.filter_by(username=username).first().id
    if user_id:
        result=UserDefinedVariables.query.filter_by(user_id=user_id).first()
        high_limit = result.higher_temp_limit if result else None
        low_limit = result.lower_temp_limit if result else None
        return high_limit,low_limit
    else:
        print('Nie ma takiego użytkownika!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # a=read_send_times_from_db_and_transform_to_string()
        # data = {
        #     "send_times": a
        # }
        # publish_to_device(data)
        setup_mqtt()  # Konfiguracja MQTT
        # publish_to_device()
        # while(True):
        #     # # send_times_to_beacon()
        #     # publish_to_device(read_frequency_from_db(),'sending_times')
        #     # publish_to_device_2(read_changed_limits_from_db(),'temperature_limits')
        #
        #     sleep(5)
        # read_changed_limits_from_db()

    app.run(debug=True)
