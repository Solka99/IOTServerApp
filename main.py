from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
from datetime import datetime
from flask import flash
from models import db, User, IoTDevice, UserDefinedVariables, SendTimes

app = Flask(__name__)
app.secret_key = 'abc'

# Konfiguracja bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iot_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# # Inicjalizacja bazy danych
# db = SQLAlchemy(app)
# Inicjalizacja bazy danych
db.init_app(app)

# MQTT klient
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code ", rc)
    client.subscribe("#")

def on_message(client, userdata, msg):
    try:
        message = msg.payload.decode('utf-8')
    except UnicodeDecodeError:
        message = msg.payload
    # print(f"Received message: {message} on topic: {msg.topic}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("mqtt.eclipseprojects.io", 1883, 60)
mqtt_client.loop_start()

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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
