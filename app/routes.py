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

        # Fetch the latest sensor reading
        cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1")
        latest_data = cursor.fetchone() or {}

        # Fetch active alerts (assuming you might want a status column later)
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC")
        active_alerts = cursor.fetchall()

        return render_template('dashboard.html',
                               data=latest_data,
                               alerts=active_alerts)  # Pass the active alerts to the template
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

ADMIN_USERS = {'Manager'}  # Replace with your actual admin usernames

def is_admin():
    current_user = 'Manager'  #replace with actual user retrieval
    return current_user in ADMIN_USERS

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not is_admin():
        return "Unauthorized Access", 403  # Or redirect to an error page

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            updated_thresholds = request.form

            for parameter, value in updated_thresholds.items():
                if parameter.endswith('_min'):
                    sensor = parameter[:-4]
                    min_value = value
                    cursor.execute("UPDATE optimal_ranges SET min_value = %s WHERE parameter = %s", (min_value, sensor))
                elif parameter.endswith('_max'):
                    sensor = parameter[:-4]
                    max_value = value
                    cursor.execute("UPDATE optimal_ranges SET max_value = %s WHERE parameter = %s", (max_value, sensor))
            conn.commit()
            return redirect(url_for('settings'))  # Redirect to refresh the page

        # Fetch current thresholds for display
        cursor.execute("SELECT parameter, min_value, max_value FROM optimal_ranges")
        thresholds = {row['parameter']: row for row in cursor.fetchall()}

        return render_template('settings.html', thresholds=thresholds)

    except Exception as e:
        app.logger.error(f"Settings error: {e}")
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()