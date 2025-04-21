import os
import mysql.connector
from mysql.connector import Error, pooling
import random
from datetime import datetime

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


def insert_sensor_data(data):
    """Inserts sensor data into MySQL and checks for alerts."""
    query_insert = """
    INSERT INTO sensor_readings
    (temperature, pressure, light_intensity, humidity, air_quality, pH, moisture)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    query_thresholds = "SELECT parameter, min_value, max_value FROM optimal_ranges"
    query_insert_alert = """
    INSERT INTO alerts (timestamp, sensor_type, reading_value, threshold_type, threshold_value)
    VALUES (%s, %s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the new sensor data
        cursor.execute(query_insert, (
            data.get('temperature'),
            data.get('pressure'),
            data.get('light_intensity'),
            data.get('humidity'),
            data.get('air_quality'),
            data.get('pH'),
            data.get('moisture')
        ))
        conn.commit()

        # Fetch current thresholds
        cursor.execute(query_thresholds)
        thresholds = {row['parameter']: {'min': row['min_value'], 'max': row['max_value']} for row in cursor.fetchall()}

        timestamp = datetime.now()

        # Iterate through the sensor data and check against thresholds
        for sensor_type, reading in data.items():
            if sensor_type in thresholds:
                min_threshold = thresholds[sensor_type]['min']
                max_threshold = thresholds[sensor_type]['max']

                if reading < min_threshold:
                    cursor.execute(query_insert_alert, (timestamp, sensor_type, reading, 'min', min_threshold))
                elif reading > max_threshold:
                    cursor.execute(query_insert_alert, (timestamp, sensor_type, reading, 'max', max_threshold))

        conn.commit()

    except Error as e:
        if conn:
            conn.rollback()
        raise RuntimeError(f"Failed to insert data or check alerts: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def simulate_sensor_data():
    """Generates fake sensor data for testing"""
    return {
        'timestamp': datetime.now(),
        'temperature': round(random.uniform(20, 30), 2),
        'pressure': round(random.uniform(1000, 1010), 2),
        'light_intensity': random.randint(500, 1000),
        'humidity': round(random.uniform(40, 60), 2),
        'air_quality': random.randint(0, 100),
        'pH': round(random.uniform(6, 8), 1),
        'moisture': round(random.uniform(20, 80), 2)
    }


def get_historical_data(start_date, end_date):
    """Fetch ALL sensor metrics with proper pH capitalization"""
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
            conn.close()