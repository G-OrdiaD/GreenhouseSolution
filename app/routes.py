from flask import render_template, request
from datetime import datetime, timedelta
from app import app
from app.utils.db_utils import get_db_connection


@app.route('/')
def dashboard():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1")
        data = cursor.fetchone()

        cursor.execute("SELECT * FROM issues WHERE status != 'resolved' ORDER BY timestamp DESC")
        issues = cursor.fetchall()

        return render_template('dashboard.html',
                               data=data or {},
                               issues=issues)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()


@app.route('/history')
def history():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        start_date = request.args.get('start', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))

        cursor.execute("""
            SELECT DATE(timestamp) as date, 
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
        """, (start_date, end_date))
        history_data = cursor.fetchall()

        cursor.execute("SELECT * FROM optimal_ranges")
        thresholds = {row['parameter']: row for row in cursor.fetchall()}

        return render_template('history.html',
                               data=history_data,
                               thresholds=thresholds,
                               start_date=start_date,
                               end_date=end_date,
                               datetime=datetime)
    except Exception as e:
        app.logger.error(f"History error: {e}")
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.errorhandler(500)
def internal_error(error):
    return "An internal error occurred. Please try again later.", 500