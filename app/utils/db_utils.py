import json
import random
from datetime import datetime
import mysql.connector
from mysql.connector import Error, pooling
from flask import current_app
from flask_login import UserMixin

connection_pool = None

def init_db(app):
    global connection_pool
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="greenhouse_pool",
            pool_size=app.config['MYSQL_POOL_SIZE'],
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )
    except Error as e:
        raise RuntimeError(f"Failed to initialize pool: {e}")


def get_db_connection():
    if not connection_pool:
        raise RuntimeError("Database pool not initialized")
    return connection_pool.get_connection()


class AnonymousUser(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


def load_user(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        if user_data:
            return AnonymousUser(**user_data)
    return None


def insert_sensor_data(data):
    conn = None
    alerts_triggered = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO sensor_readings (timestamp, temperature, pressure, light_intensity, humidity, air_quality, pH, moisture, greenhouse_zone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['timestamp'],
            data.get('temperature'),
            data.get('pressure'),
            data.get('light_intensity'),
            data.get('humidity'),
            data.get('air_quality'),
            data.get('pH'),
            data.get('moisture'),
            data.get('greenhouse_zone')
        ))
        # Get thresholds
        cursor.execute("SELECT parameter, min_value, max_value FROM optimal_ranges")
        thresholds = {row['parameter']: row for row in cursor.fetchall()}

        for param in ['temperature', 'humidity', 'light_intensity',
                      'pressure', 'air_quality', 'pH', 'moisture']:
            value = data.get(param)
            if value is None:
                continue

            if param in thresholds:
                min_val = thresholds[param]['min_value']
                max_val = thresholds[param]['max_value']

                current_app.logger.info(f"Checking {param}: value={value}, min={min_val}, max={max_val}") # Added logging

                # Check min threshold
                if min_val is not None and value < min_val:
                    alert_msg = f"{param} too low ({value} < {min_val})"
                    cursor.execute("""
                        INSERT INTO alerts (message, timestamp, sensor_type, reading_value, threshold_type, threshold_value, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (alert_msg, data['timestamp'], param, float(value), 'min', float(min_val), 'Open'))
                    alerts_triggered.append(alert_msg)

                # Check max threshold
                if max_val is not None and value > max_val:
                    alert_msg = f"{param} too high ({value} > {max_val})"
                    cursor.execute("""
                        INSERT INTO alerts (message, timestamp, sensor_type, reading_value, threshold_type, threshold_value, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (alert_msg, data['timestamp'], param, float(value), 'max', float(max_val), 'Open'))
                    alerts_triggered.append(alert_msg)

        conn.commit()
        return alerts_triggered

    except Error as e:
        if conn:
            conn.rollback()
        current_app.logger.error(f"Database error: {e}")
        raise RuntimeError(f"Failed to process sensor data: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def simulate_sensor_data():
    data = {
        'timestamp': datetime.now().isoformat() + 'Z',
        'temperature': round(random.uniform(10, 50), 2),  # WIDER RANGE
        'pressure': round(random.uniform(980, 1030), 2),  # WIDER RANGE
        'light_intensity': random.randint(200, 1500),  # Wider
        'humidity': round(random.uniform(10, 90), 2),  # wider
        'air_quality': random.randint(10, 200),  # VERY BAD air
        'pH': round(random.uniform(3.5, 9.0), 1),  # pH extremes
        'moisture': round(random.uniform(10, 90), 2),  # dry to soaked
        'greenhouse_zone': random.choice(['Zone A', 'Zone B', 'Zone C'])  # Just random zones
    }
    json_payload = json.dumps(data)
    print(f"Simulated JSON Payload: {json_payload}")
    return data


def get_historical_data(start_date, end_date):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT
            DATE(timestamp) as date,
            AVG(temperature) as avg_temp,
            AVG(pressure) as avg_pressure,
            AVG(light_intensity) as avg_light,
            AVG(humidity) as avg_humidity,
            AVG(air_quality) as avg_air_quality,
            AVG(pH) as avg_ph,
            AVG(moisture) as avg_moisture
        FROM sensor_readings
        WHERE timestamp BETWEEN %s AND %s
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        """

        cursor.execute(query, (start_date, end_date))
        return cursor.fetchall()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()