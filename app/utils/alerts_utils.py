from .db_utils import get_db_connection
from datetime import datetime

THRESHOLDS = {
    'temperature': {'min': 18, 'max': 40},
    'humidity': {'min': 30, 'max': 80},
    'light_intensity': {'min': 150, 'max': 1800},
    'pressure': {'min': 985, 'max': 1040},
    'air_quality': {'min': 0, 'max': 100},
    'pH': {'min': 6.0, 'max': 7.5},
    'moisture': {'min': 15, 'max': 55}
}

def check_and_generate_alerts(sensor_data):
    connection = get_db_connection()
    cursor = connection.cursor()

    for sensor, limits in THRESHOLDS.items():
        value = sensor_data.get(sensor)
        if value is None:
            continue

        if value < limits['min']:
            cursor.execute('''
                INSERT INTO alerts (sensor_type, reading_value, threshold_type, threshold_value, timestamp, status)
                VALUES (%s, %s, 'min', %s, %s, 'Unresolved')
            ''', (sensor, value, limits['min'], datetime.now()))

        elif value > limits['max']:
            cursor.execute('''
                INSERT INTO alerts (sensor_type, reading_value, threshold_type, threshold_value, timestamp, status)
                VALUES (%s, %s, 'max', %s, %s, 'Unresolved')
            ''', (sensor, value, limits['max'], datetime.now()))

    connection.commit()
    connection.close()
