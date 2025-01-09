# Importujemy wymagane moduły
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

# Konfiguracja bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iot_app.db'  # Na początek SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modele bazodanowe
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class IoTDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    config = db.Column(db.String(200), nullable=True)  # Przechowywanie konfiguracji urządzenia

# Aktualnie zalogowany użytkownik (prosty mechanizm sesji w pamięci)
current_user = None

# Endpoint do rejestracji użytkownika
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    new_user = User(username=data['username'], password=data['password'])  # Brak haszowania
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'}), 201

# Endpoint do logowania użytkownika
@app.route('/login', methods=['POST'])
def login():
    global current_user
    data = request.get_json()
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    if not user:
        return jsonify({'message': 'Invalid credentials!'}), 401

    current_user = user
    return jsonify({'message': f'User {user.username} logged in successfully!'}), 200

# Endpoint do przypisywania urządzenia do użytkownika
@app.route('/devices', methods=['POST'])
def add_device():
    if not current_user:
        return jsonify({'message': 'No user logged in!'}), 401

    data = request.get_json()
    device = IoTDevice.query.filter_by(name=data['name']).first()
    if device and device.owner_id is not None:
        return jsonify({'message': 'Device is already registered by another user!'}), 400

    if not device:
        device = IoTDevice(name=data['name'], owner_id=current_user.id)
    else:
        device.owner_id = current_user.id

    db.session.add(device)
    db.session.commit()
    return jsonify({'message': 'Device registered successfully!'}), 201

# Endpoint do wizualizacji danych z urządzenia
@app.route('/devices/<int:device_id>/data', methods=['GET'])
def get_device_data(device_id):
    if not current_user:
        return jsonify({'message': 'No user logged in!'}), 401

    device = IoTDevice.query.filter_by(id=device_id, owner_id=current_user.id).first()
    if not device:
        return jsonify({'message': 'Device not found or not owned by the user!'}), 404

    # Placeholder danych - w rzeczywistości dane będą pochodzić z MQTT
    data = {
        'temperature': 25.5,
        'humidity': 60,
        'alarm': False
    }
    return jsonify(data)

# Endpoint do konfiguracji urządzenia
@app.route('/devices/<int:device_id>/config', methods=['POST'])
def configure_device(device_id):
    if not current_user:
        return jsonify({'message': 'No user logged in!'}), 401

    device = IoTDevice.query.filter_by(id=device_id, owner_id=current_user.id).first()
    if not device:
        return jsonify({'message': 'Device not found or not owned by the user!'}), 404

    data = request.get_json()
    device.config = data.get('config', '')
    db.session.commit()
    return jsonify({'message': 'Device configured successfully!'}), 200

#Endpoint home
@app.route('/')
def home():
    return "Welcome to the IoT server!"

# Uruchomienie aplikacji
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Tworzy tabele w bazie danych
    app.run(debug=True)

