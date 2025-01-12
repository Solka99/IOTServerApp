from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
from datetime import datetime
from flask import flash

app = Flask(__name__)
app.secret_key = 'abc'

# Konfiguracja bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iot_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicjalizacja bazy danych
db = SQLAlchemy(app)

# Modele bazodanowe
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    variables = db.relationship('UserDefinedVariables', backref='user', lazy=True)

class IoTDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    config = db.Column(db.String(200), nullable=True)  # Przechowywanie konfiguracji urządzenia

class UserDefinedVariables(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),  primary_key=True, nullable=True)
    lower_temp_limit = db.Column(db.Integer, nullable=True)
    higher_temp_limit = db.Column(db.Integer, nullable=True)

    # Relacja do tabeli SendTimes
    send_times = db.relationship('SendTimes', backref='variables', lazy=True)


class SendTimes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variables_id = db.Column(db.Integer, db.ForeignKey('user_defined_variables.user_id'), nullable=False)
    send_time = db.Column(db.Time, nullable=False)  # Przechowuje konkretną godzinę wysyłania

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
        return jsonify({'redirect': url_for('set_parameters')}), 200
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
