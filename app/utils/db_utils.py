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
            data['temperature'],
            data['pressure'],
            data['light_intensity'],
            data['humidity'],
            data['air_quality'],
            data['pH'],
            data['moisture']
        ))
        conn.commit()

        # Fetch current thresholds
        cursor.execute(query_thresholds)
        thresholds = {row['parameter']: {'min': row['min_value'], 'max': row['max_value']} for row in cursor.fetchall()}

        timestamp = datetime.now()

        # Check for alerts
        if 'temperature' in data and 'temperature' in thresholds:
            if data['temperature'] < thresholds['temperature']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'temperature', data['temperature'], 'min', thresholds['temperature']['min']))
            elif data['temperature'] > thresholds['temperature']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'temperature', data['temperature'], 'max', thresholds['temperature']['max']))

        if 'pressure' in data and 'pressure' in thresholds:
            if data['pressure'] < thresholds['pressure']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'pressure', data['pressure'], 'min', thresholds['pressure']['min']))
            elif data['pressure'] > thresholds['pressure']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'pressure', data['pressure'], 'max', thresholds['pressure']['max']))

        if 'light_intensity' in data and 'light_intensity' in thresholds:
            if data['light_intensity'] < thresholds['light_intensity']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'light_intensity', data['light_intensity'], 'min', thresholds['light_intensity']['min']))
            elif data['light_intensity'] > thresholds['light_intensity']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'light_intensity', data['light_intensity'], 'max', thresholds['light_intensity']['max']))

        if 'humidity' in data and 'humidity' in thresholds:
            if data['humidity'] < thresholds['humidity']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'humidity', data['humidity'], 'min', thresholds['humidity']['min']))
            elif data['humidity'] > thresholds['humidity']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'humidity', data['humidity'], 'max', thresholds['humidity']['max']))

        if 'air_quality' in data and 'air_quality' in thresholds:
            if data['air_quality'] < thresholds['air_quality']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'air_quality', data['air_quality'], 'min', thresholds['air_quality']['min']))
            elif data['air_quality'] > thresholds['air_quality']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'air_quality', data['air_quality'], 'max', thresholds['air_quality']['max']))

        if 'pH' in data and 'pH' in thresholds:
            if data['pH'] < thresholds['pH']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'pH', data['pH'], 'min', thresholds['pH']['min']))
            elif data['pH'] > thresholds['pH']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'pH', data['pH'], 'max', thresholds['pH']['max']))

        if 'moisture' in data and 'moisture' in thresholds:
            if data['moisture'] < thresholds['moisture']['min']:
                cursor.execute(query_insert_alert, (timestamp, 'moisture', data['moisture'], 'min', thresholds['moisture']['min']))
            elif data['moisture'] > thresholds['moisture']['max']:
                cursor.execute(query_insert_alert, (timestamp, 'moisture', data['moisture'], 'max', thresholds['moisture']['max']))

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