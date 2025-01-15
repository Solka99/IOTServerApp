from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Modele bazodanowe
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    variables = db.relationship('UserDefinedVariables', backref='user', lazy=True)

class IoTDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=False, nullable=False)  # Unikalny identyfikator urządzenia
    name = db.Column(db.String(100), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    config = db.Column(db.JSON, nullable=True)  # Przechowywanie konfiguracji urządzenia  <-- do dodania jak ogarniemy co ma być w configu
    registered_at = db.Column(db.DateTime, default=datetime.now)  # Data rejestracji urządzenia


class UserDefinedVariables(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),  primary_key=True, nullable=True)
    lower_temp_limit = db.Column(db.Integer, nullable=True)
    higher_temp_limit = db.Column(db.Integer, nullable=True)
    frequency = db.Column(db.Integer, nullable=True)

    # Relacja do tabeli SendTimes
    send_times = db.relationship('SendTimes', backref='variables', lazy=True)


class SendTimes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    variables_id = db.Column(db.Integer, db.ForeignKey('user_defined_variables.user_id'), nullable=False)
    send_time = db.Column(db.Time, nullable=False)  # Przechowuje konkretną godzinę wysyłania


class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), db.ForeignKey('io_t_device.device_id'), nullable=False)  # Powiązanie z urządzeniem
    temperature = db.Column(db.Float, nullable=False)
    pressure = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)  # Czas zapisania danych

