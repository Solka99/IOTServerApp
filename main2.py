from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt

app = Flask(__name__)

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
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    lower_temp_limit = db.Column(db.Float, nullable=True)
    higher_temp_limit = db.Column(db.Float, nullable=True)

    # Relacja do tabeli SendTimes
    send_times = db.relationship('SendTimes', backref='variables', lazy=True)


class SendTimes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variables_id = db.Column(db.Integer, db.ForeignKey('user_defined_variables.id'), nullable=False)
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
        return jsonify({'message': f'Welcome, {user.username}!'}), 200

    return jsonify({'error': 'Invalid username or password!'}), 401
@app.route('/set_parameters', methods=['POST'])
def set_parameters():
    data = request.get_json()
    user_id = data.get('user_id')
    lower_temp_limit = data.get('lower_temp_limit')
    higher_temp_limit = data.get('higher_temp_limit')
    send_times = data.get('send_times')  # Lista godzin, np. ["08:00", "12:00", "18:00"]

    # Znajdź lub utwórz zmienne użytkownika
    user_variables = UserDefinedVariables.query.filter_by(user_id=user_id).first()
    if not user_variables:
        user_variables = UserDefinedVariables(user_id=user_id)

    user_variables.lower_temp_limit = lower_temp_limit
    user_variables.higher_temp_limit = higher_temp_limit

    # Usuń istniejące godziny wysyłania i dodaj nowe
    SendTimes.query.filter_by(variables_id=user_variables.id).delete()
    for time in send_times:
        send_time = SendTimes(variables_id=user_variables.id, send_time=time)
        db.session.add(send_time)

    db.session.add(user_variables)
    db.session.commit()

    return jsonify({'message': 'Parameters updated successfully!'}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
