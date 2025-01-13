from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
from datetime import datetime
from flask import flash
import json
from models import db, User, IoTDevice, UserDefinedVariables, SendTimes, SensorData
import os


# Dane do wysłania
# mosquitto_pub -h 127.0.0.1 -p 1883 -t "user1/device1/temperature" -m '{\"value\": 25.5}'


app = Flask(__name__)
app.secret_key = 'abc'

# Konfiguracja bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iot_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# # Inicjalizacja bazy danych
# db = SQLAlchemy(app)
# Inicjalizacja bazy danych
db.init_app(app)


# MQTT konfiguracja
BROKER_URL = "127.0.0.1"
BROKER_PORT = 1883

USERNAME = "user1"
PASSWORD = "user1"

TOPICS = [
    "user1/+/temperature"
]
# Modele bazy danych
class SensorData2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

# # Funkcja zapisu danych do bazy danych
# def save_data_to_db(topic, value):
#     try:
#         timestamp = datetime.utcnow()
#         new_data = SensorData2(topic=topic, value=value, timestamp=timestamp)
#         db.session.add(new_data)
#         db.session.commit()
#         print(f"Saved to DB: {topic} -> {value} at {timestamp}")
#     except Exception as e:
#         print(f"Error saving to database: {e}")

def save_data_to_db(topic, value):
    with app.app_context():  # Wymuszenie kontekstu aplikacji
        try:
            timestamp = datetime.now()
            # Konwersja wartości na ciąg znaków JSON
            value_str = json.dumps(value)  # Zamienia słownik na JSON w formie tekstu
            new_data = SensorData2(topic=topic, value=value_str, timestamp=timestamp)
            db.session.add(new_data)
            db.session.commit()
            print(f"Saved to DB: {topic} -> {value_str} at {timestamp}")
        except Exception as e:
            print(f"Error saving to database: {e}")




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

# # MQTT klient
# def on_connect(client, userdata, flags, rc):
#     print("Connected to MQTT broker with result code ", rc)
#     client.subscribe("#")
#
# # def on_message(client, userdata, msg):
# #     try:
# #         message = msg.payload.decode('utf-8')
# #     except UnicodeDecodeError:
# #         message = msg.payload
# #     # print(f"Received message: {message} on topic: {msg.topic}")
#
#
# def on_message(client, userdata, msg):
#     try:
#         payload = json.loads(msg.payload.decode('utf-8'))
#         device_id = payload.get('device_id')
#         temperature = payload.get('temperature')
#         pressure = payload.get('pressure')
#
#         # Weryfikacja urządzenia
#         device = IoTDevice.query.filter_by(device_id=device_id).first()
#         if not device:
#             print(f"Invalid device ID: {device_id}")
#             return
#
#         # Zapis danych do bazy
#         new_data = SensorData(device_id=device_id, temperature=temperature, pressure=pressure)
#         db.session.add(new_data)
#         db.session.commit()
#         print(f"Data saved: {device_id}, Temp: {temperature}, Pressure: {pressure}")
#     except Exception as e:
#         print(f"Error processing message: {e}")


# mqtt_client = mqtt.Client()
# mqtt_client.on_connect = on_connect
# mqtt_client.on_message = on_message
# mqtt_client.connect("mqtt.eclipseprojects.io", 1883, 60)
# mqtt_client.loop_start()

@app.route('/')
def home():
    return render_template('index.html')

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

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user_id'] = user.id  # Przechowujemy user_id w sesji
        return jsonify({'redirect': url_for('dashboard')}), 200
        # return jsonify({'message': f'Welcome, {user.username}!'}), 200

    return jsonify({'error': 'Invalid username or password!'}), 401


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
        send_times = request.form.get('send_times')

        # Walidacja godzin (send_times)
        valid_times = []
        if send_times:
            for time_str in send_times.split(','):
                time_str = time_str.strip()
                try:
                    # Konwersja na obiekt czasu
                    time_obj = datetime.strptime(time_str, '%H:%M').time()
                    valid_times.append(time_obj)
                except ValueError:
                    # Jeśli format jest nieprawidłowy
                    return render_template(
                        'set_parameters.html',
                        lower_temp_limit=lower_temp_limit,
                        higher_temp_limit=higher_temp_limit,
                        send_times=send_times,
                        error=f"Invalid time format: '{time_str}'. Use HH:MM format."
                    )

        # Jeśli brak zmiennych użytkownika, utwórz je
        if not user_variables:
            user_variables = UserDefinedVariables(user_id=user_id)
            db.session.add(user_variables)

        # Zapisz nowe wartości
        user_variables.lower_temp_limit = int(lower_temp_limit) if lower_temp_limit else None
        user_variables.higher_temp_limit = int(higher_temp_limit) if higher_temp_limit else None

        # Aktualizuj godziny wysyłania
        SendTimes.query.filter_by(variables_id=user_variables.user_id).delete()  # Usuń poprzednie godziny
        if send_times:
            for time_str in send_times.split(','):
                time_obj = datetime.strptime(time_str.strip(), '%H:%M').time()
                db.session.add(SendTimes(variables=user_variables, send_time=time_obj))

        db.session.commit()
        flash('Parameters set successfully!', 'success')
        return redirect(url_for('set_parameters'))

    # Przygotuj dane do wyświetlenia w formularzu
    lower_temp_limit = user_variables.lower_temp_limit if user_variables else ''
    higher_temp_limit = user_variables.higher_temp_limit if user_variables else ''
    send_times = (
        ', '.join([time.send_time.strftime('%H:%M') for time in user_variables.send_times])
        if user_variables and user_variables.send_times
        else ''
    )

    return render_template(
        'set_parameters.html',
        lower_temp_limit=lower_temp_limit,
        higher_temp_limit=higher_temp_limit,
        send_times=send_times
    )

@app.route('/register_device', methods=['POST'])
def register_device():
    print('in')
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
            device.registered_at = datetime.utcnow()
            db.session.commit()
            return jsonify({
                'message': f'Device {device.device_id} is now registered to your account. '
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

    device_ids = [device.device_id for device in user_devices]
    data = SensorData.query.filter(SensorData.device_id.in_(device_ids)).order_by(SensorData.timestamp.desc()).all()

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

@app.route('/publish_to_device', methods=['POST'])
def publish_to_device():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized access!'}), 403

    user_id = session['user_id']

    # Pobierz dane użytkownika z bazy danych
    user_variables = UserDefinedVariables.query.filter_by(user_id=user_id).first()
    if not user_variables:
        return jsonify({'error': 'No parameters set for this user!'}), 404

    # Utwórz payload z danymi
    payload = {
        "lower_temp_limit": user_variables.lower_temp_limit,
        "higher_temp_limit": user_variables.higher_temp_limit,
        "send_times": [time.send_time.strftime('%H:%M') for time in user_variables.send_times]
    }

    try:
        # Konfiguracja klienta MQTT
        client = mqtt.Client()
        client.username_pw_set(USERNAME, PASSWORD)
        client.connect(BROKER_URL, BROKER_PORT, 60)

        # Publikacja danych
        topic = f"user{user_id}/device/config"
        client.publish(topic, json.dumps(payload))
        client.disconnect()

        return jsonify({'message': 'Configuration published to device!'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to publish data: {str(e)}'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        setup_mqtt()  # Konfiguracja MQTT
    app.run(debug=True)
