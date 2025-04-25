from random import randint
from datetime import datetime, timedelta
from functools import wraps
import re
from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import sys
from itsdangerous import URLSafeTimedSerializer
from twilio.base.exceptions import TwilioRestException
from flask_login import current_user, login_required
from app import app
from app.utils.db_utils import get_db_connection, insert_sensor_data
from app.forms import LoginForm, RegistrationForm, AddGreenhouseForm, AlertSettingsForm
from twilio.rest import Client


# HELPER FUNCTIONS
def require_role(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_logged_in():  # Fixed function name
                return redirect(url_for('login'))
            current_user_role = session.get('role')
            if current_user_role in roles:
                return f(*args, **kwargs)
            return "Unauthorized Access", 403
        return decorated_function
    return decorator

def is_admin():
    """Check if current user is admin"""
    return session.get('role') == 'Manager'

def is_logged_in():
    """Check if user is logged in"""
    return 'user_id' in session

def validate_phone(phone_number):
    """Validate phone number format"""
    return re.match(r'^\+?[0-9]{10,15}$', phone_number)


# MIDDLEWARE
@app.before_request
def require_login():
    """Ensure user is logged in for protected routes"""
    if request.endpoint in ['login', 'register', 'static', 'reset_password_request', 'verify_otp', 'reset_password']:
        return
    if not is_logged_in():
        return redirect(url_for('login'))


# AUTHENTICATION ROUTES
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():

        username = form.username.data
        email = form.email.data
        phone_number = form.phone_number.data
        password = form.password.data

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Check if user already exists
            cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s OR phone_number = %s",
                (username, email, phone_number)
            )
            if cursor.fetchone():
                flash('Username, email or phone already exists.', 'error')
                return render_template('register.html', form=form)

            # Insert new user
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, email, phone_number, password_hash) VALUES (%s, %s, %s, %s)",
                (username, email, phone_number, hashed_password)
            )
            conn.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            app.logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html', form=form)

        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

            print(sys.path)
            pass
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        identifier = form.identifier.data
        password = form.password.data

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                        SELECT id, username, password_hash, role
                        FROM users
                        WHERE username = %s OR email = %s OR phone_number = %s
                        """, (identifier, identifier, identifier))
            user = cursor.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))

            flash('Invalid credentials', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# PASSWORD RESET ROUTES
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Password reset initiation"""
    if request.method == 'POST':
        phone_number = request.form['phone_number']

        if not validate_phone(phone_number):
            flash('Invalid phone number format', 'error')
            return redirect(url_for('reset_password_request'))

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE phone_number = %s", (phone_number,))
            user = cursor.fetchone()
            if user:
                otp = randint(100000, 999999)
                session['reset_otp'] = str(otp)
                session['reset_phone'] = phone_number
                session['otp_expiry'] = datetime.now() + timedelta(minutes=10)
                try:
                    message = current_app.twilio_client.messages.create(
                        body=f'Your OTP is: {otp} (valid for 5 mins)',
                        from_=current_app.config['TWILIO_PHONE_NUMBER'],
                        to=phone_number
                    )
                    flash('OTP sent to your phone', 'info')
                    return redirect(url_for('verify_otp'))
                except TwilioRestException as e:
                    app.logger.error(f"Twilio error: {e}")
                    flash('Failed to send OTP. Please try again.', 'error')
            flash('If registered, you will receive an OTP shortly', 'info')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Reset request error: {e}")
            flash('An error occurred. Please try again.', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('reset_password_request.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """OTP verification for password reset"""
    if 'reset_phone' not in session:
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        user_otp = request.form['otp']
        if (session.get('reset_otp') == user_otp and
                datetime.now() < session['otp_expiry']):
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))
        flash('Invalid or expired OTP', 'error')
    return render_template('verify_otp.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Password reset handler"""
    if not session.get('otp_verified'):
        flash('Please verify OTP first', 'error')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('reset_password'))
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return redirect(url_for('reset_password'))

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE phone_number = %s",
                (generate_password_hash(password), session['reset_phone'])
            )
            conn.commit()
            for key in ['reset_otp', 'otp_verified', 'reset_phone', 'otp_expiry']:
                session.pop(key, None)
            flash('Password updated successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            if conn:
                conn.rollback()
            app.logger.error(f"Password reset error: {e}")
            flash('An error occurred. Please try again.', 'error')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('reset_password.html')


# DASHBOARD ROUTES
@app.route('/')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get latest sensor data
        cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1")
        latest_data = cursor.fetchone() or {}

        # Get active alerts (only non-resolved)
        cursor.execute("""
            SELECT 
                sensor_type, reading_value,
                threshold_type, threshold_value,
                timestamp, status
            FROM alerts
            WHERE status != 'Resolved'
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        alerts = cursor.fetchall()
        return render_template('dashboard.html', data=latest_data, alerts=alerts)

    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}")
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/history')
def history():
    """Historical data route"""
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        start_date = request.args.get('start', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        cursor.execute("""
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
        """, (start_date, end_date))
        history_data = cursor.fetchall()
        return render_template('history.html', data=history_data, start_date=start_date, end_date=end_date, now=datetime.now)
    except Exception as e:
        app.logger.error(f"History error: {e}")
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# MANAGEMENT ROUTES
@app.route('/greenhouses')
@require_role(['Manager'])
def greenhouses():
    """Greenhouse management - display list"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, location, description FROM greenhouses ORDER BY name")
        greenhouses = cursor.fetchall()
        return render_template('greenhouses.html', greenhouses=greenhouses)
    except Exception as e:
        app.logger.error(f"Greenhouse error: {e}")
        flash('Error retrieving greenhouse data.', 'error')
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/settings', methods=['GET', 'POST'])
@require_role(['Manager'])
def settings():
    """System settings management"""
    form = AlertSettingsForm()
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST' and form.validate_on_submit(): # Check if form is submitted and valid
            for param, value in request.form.items():
                if param.endswith('_min'):
                    cursor.execute(
                        "UPDATE optimal_ranges SET min_value = %s WHERE parameter = %s",
                        (value, param[:-4])
                    )
                elif param.endswith('_max'):
                    cursor.execute(
                        "UPDATE optimal_ranges SET max_value = %s WHERE parameter = %s",
                        (value, param[:-4])
                    )
            conn.commit()
            flash('Settings updated successfully', 'success')
            return redirect(url_for('settings'))
        cursor.execute("SELECT * FROM optimal_ranges")
        thresholds = {row['parameter']: row for row in cursor.fetchall()}
        return render_template('alert_settings.html', thresholds=thresholds, form=form)
    except Exception as e:
        app.logger.error(f"Settings error: {e}")
        flash('Failed to update settings', 'error')
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/greenhouses/add', methods=['GET', 'POST'])
@require_role(['Manager'])
def add_greenhouse():
    """Add a new greenhouse"""
    form = AddGreenhouseForm()
    if form.validate_on_submit():
        name = form.name.data
        location = form.location.data
        description = form.description.data
        if not name:
            flash('Name is required to add a greenhouse.', 'error')
            return render_template('add_greenhouse.html', form=form)
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO greenhouses (name, location, description) VALUES (%s, %s, %s)",
                (name, location, description)
            )
            conn.commit()
            flash(f'Greenhouse "{name}" added successfully!', 'success')
            return redirect(url_for('greenhouses'))
        except Exception as e:
            app.logger.error(f"Error adding greenhouse: {e}")
            flash('Error adding the greenhouse. Please try again.', 'error')
            return render_template('add_greenhouse.html', form=form)
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('add_greenhouse.html', form=form)


@app.route('/assignments', methods=['GET', 'POST'])
@require_role(['Manager'])
def manage_assignments(greenhouse_id=None):
    """Manage employee assignments to greenhouses."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, username FROM users WHERE role = 'Employee'")
        employees = cursor.fetchall()
        cursor.execute("SELECT id, name FROM greenhouses")
        greenhouses = cursor.fetchall()

        assigned_employees = []
        if greenhouse_id:
            cursor.execute("SELECT employee_id FROM employee_assignments WHERE greenhouse_id = %s", (greenhouse_id,))
            assigned_employees = [row['employee_id'] for row in cursor.fetchall()]

        return render_template(
            'manage_assignments.html',
            employees=employees,
            greenhouses=greenhouses,
            assigned_employees=assigned_employees,
            current_greenhouse_id=greenhouse_id
        )
    except Exception as e:
        app.logger.error(f"Manage assignments error: {e}")
        flash('Error managing assignments. Please try again.', 'error')
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# API ROUTES
@app.route('/api/submit_feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Feedback submission API"""
    try:
        data = request.get_json()
        feedback_text = data.get('feedback')
        related_table = data.get('related_table')
        related_id = data.get('related_id')

        if not feedback_text:
            return jsonify({'success': False, 'error': 'Feedback text required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (user_id, feedback_text, related_table, related_id) VALUES (%s, %s, %s, %s)",
            (session['user_id'], feedback_text, related_table, related_id)
        )
        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Feedback error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/latest_sensor_data')
def latest_sensor_data():
    """Returns the latest sensor data as JSON."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1")
        latest_data = cursor.fetchone()
        return jsonify(latest_data or {})
    except Exception as e:
        app.logger.error(f"Error fetching latest sensor data: {e}")
        return jsonify({}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# Add this decorator above your API route
@app.route('/receive_sensor_data', methods=['POST'])
def receive_sensor_data():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        data = request.get_json()
        required_sensors = [
            'temperature', 'humidity', 'light_intensity', 'pressure', 'air_quality', 'pH', 'moisture'
        ]

        for sensor in required_sensors:
            if sensor not in data:
                return jsonify({"error": f"Missing sensor data: {sensor}"}), 400

        # Process data and get alerts
        alerts = insert_sensor_data(data)

        # Send SMS for each alert if Twilio is configured
        if alerts and app.twilio_client:
            for alert in alerts:
                send_alert_sms(alert)

        return jsonify({
            "status": "success",
            "alerts": alerts,
            "sensors_received": list(data.keys())  # Verification
        }), 201

    except Exception as e:
        app.logger.error(f"Sensor processing failed: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def send_alert_sms(alert_message):
    """Send SMS to all admins when an alert triggers."""
    if not app.twilio_client:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT phone_number FROM users WHERE role = 'Manager'")
        admins = cursor.fetchall()

        for admin in admins:
            app.twilio_client.messages.create(
                body=f"🚨 ALERT: {alert_message}",
                from_=app.config['TWILIO_PHONE_NUMBER'],
                to=admin['phone_number']
            )
        return True
    except TwilioRestException as e:
        app.logger.error(f"Twilio SMS failed: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/alerts')
def get_alerts():
    """Returns the latest active alerts as JSON."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                sensor_type, reading_value,
                threshold_type, threshold_value,
                timestamp, status, message
            FROM alerts
            WHERE status != 'Resolved'
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        alerts = cursor.fetchall()
        return jsonify(alerts)
    except Exception as e:
        app.logger.error(f"Error fetching alerts: {e}")
        return jsonify({'error': 'Failed to fetch alerts'}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

# ERROR HANDLERS
@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', message="Access forbidden"), 403


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message="Internal server error"), 500