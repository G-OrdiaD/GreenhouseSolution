from flask import render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime, timedelta
from app import app
from app.utils.db_utils import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import re
from random import randint
from itsdangerous import URLSafeTimedSerializer
from twilio.base.exceptions import TwilioRestException
from functools import wraps


def require_role(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user_role = session.get('role')
            if current_user_role in roles:
                return f(*args, **kwargs)
            else:
                return "Unauthorized Access", 403  # Or redirect to an error page
        return decorated_function
    return decorator


ADMIN_USERS = {'Manager'}

def is_admin():
    # Retrieve current user role from session
    current_user_role = session.get('role')
    return current_user_role == 'Manager'

def is_logged_in():
    return 'user_id' in session

@app.before_request
def require_login():
    if not request.endpoint in ['login', 'register', 'static'] and not is_logged_in():
        return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def dashboard():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the latest sensor reading
        cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 1")
        latest_data = cursor.fetchone() or {}

        # Fetch active alerts
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC")
        active_alerts = cursor.fetchall()

        return render_template('dashboard.html',
                               data=latest_data,
                               alerts=active_alerts)
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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not email or not phone_number or not password or not confirm_password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        # Basic email and phone number validation (you might want more robust validation)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address.', 'error')
            return render_template('register.html')

        if not re.match(r"^[0-9]{10,}$", phone_number): # Example: at least 10 digits
            flash('Invalid phone number.', 'error')
            return render_template('register.html')

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if username, email, or phone number already exist
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s OR phone_number = %s", (username, email, phone_number))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('Username, email, or phone number already exists.', 'error')
                return render_template('register.html')

            # Hash the password
            hashed_password = generate_password_hash(password)

            # Insert the new user into the database
            cursor.execute("INSERT INTO users (username, email, phone_number, password_hash) VALUES (%s, %s, %s, %s)",
                           (username, email, phone_number, hashed_password))
            conn.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'] # Can be username, email, or phone number
        password = request.form['password']

        if not identifier or not password:
            flash('Username/Email/Phone and password are required.', 'error')
            return render_template('login.html')

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Try to find the user by username, email, or phone number
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
            else:
                flash('Invalid username/email/phone or password.', 'error')
                return render_template('login.html')

        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    return render_template('login.html')



@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        phone_number = request.form['phone_number']

        if not re.match(r'^\+?[0-9]{10,15}$', phone_number):
            flash('Invalid phone number format. Include country code (e.g., +1234567890)', 'error')
            return redirect(url_for('reset_password_request'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE phone_number = %s", (phone_number,))
        user = cursor.fetchone()
        conn.close()

        if user:
            otp = randint(100000, 999999)
            session['reset_otp'] = str(otp)
            session['reset_phone'] = phone_number
            session['otp_expiry'] = datetime.now() + timedelta(minutes=10)

            try:
                # Send OTP via Twilio
                message = current_app.twilio_client.messages.create(
                    body=f'Your GreenhouseSolutions OTP is: {otp} (valid for 10 minutes)',
                    from_=current_app.config['TWILIO_PHONE_NUMBER'],
                    to=phone_number
                )
                flash('OTP sent to your phone', 'info')
                return redirect(url_for('verify_otp'))
            except TwilioRestException as e:
                app.logger.error(f"Twilio error: {e}")
                flash('Failed to send OTP. Please try again.', 'error')

        flash('If this number is registered, you will receive an OTP shortly.', 'info')
        return redirect(url_for('login'))

    return render_template('reset_password_request.html')


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_phone' not in session:
        flash('Password reset session expired', 'error')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        user_otp = request.form['otp']

        if (session.get('reset_otp') == user_otp and
                datetime.now() < session['otp_expiry']):
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))

        flash('Invalid or expired OTP', 'error')
        return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
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

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE phone_number = %s",
                (generate_password_hash(password), session['reset_phone'])
            )
            conn.commit()

            # Cleanup session
            session.pop('reset_otp', None)
            session.pop('otp_verified', None)
            session.pop('reset_phone', None)
            session.pop('otp_expiry', None)

            flash('Password updated successfully!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            app.logger.error(f"Password reset error: {e}")
            flash('An error occurred. Please try again.', 'error')
        finally:
            conn.close()

    return render_template('reset_password.html')  # Fixed template name

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


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
            flash('Threshold settings updated successfully.', 'success')
            return redirect(url_for('settings'))  # Redirect to refresh the page

        # Fetch current thresholds for display
        cursor.execute("SELECT parameter, min_value, max_value FROM optimal_ranges")
        thresholds = {row['parameter']: row for row in cursor.fetchall()}

        return render_template('alert_settings.html', thresholds=thresholds)

    except Exception as e:
        app.logger.error(f"Settings error: {e}")
        flash('An error occurred while updating settings. Please try again.', 'error')
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/greenhouses')
@require_role(['Manager'])
def greenhouses():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM greenhouses ORDER BY name")
        all_greenhouses = cursor.fetchall()
        return render_template('greenhouses.html', greenhouses=all_greenhouses)
    except Exception as e:
        app.logger.error(f"Error fetching greenhouses: {e}")
        flash('An error occurred while fetching the list of greenhouses.', 'error')
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/add_greenhouse', methods=['GET', 'POST'])
@require_role(['Manager'])
def add_greenhouse():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        description = request.form['description']

        if not name:
            flash('Greenhouse name is required.', 'error')
            return render_template('manage_greenhouses.html')

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO greenhouses (name, location, description) VALUES (%s, %s, %s)",
                           (name, location, description))
            conn.commit()
            flash(f'Greenhouse "{name}" added successfully.', 'success')
            return redirect(url_for('greenhouses'))
        except Exception as e:
            app.logger.error(f"Error adding greenhouse: {e}")
            flash('An error occurred while adding the greenhouse.', 'error')
            return render_template('manage_greenhouses.html')
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template('manage_greenhouses.html')

@app.route('/manage_assignments', methods=['GET', 'POST'])
@require_role(['Manager'])
def manage_assignments():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch all employees (users with role 'Employee')
        cursor.execute("SELECT id, username FROM users WHERE role = 'Employee' ORDER BY username")
        employees = cursor.fetchall()

        # Fetch all greenhouses
        cursor.execute("SELECT id, name FROM greenhouses ORDER BY name")
        greenhouses = cursor.fetchall()

        # Fetch current assignments
        cursor.execute("SELECT user_id, greenhouse_id FROM greenhouse_assignments")
        assignments = {(assignment['user_id'], assignment['greenhouse_id']) for assignment in cursor.fetchall()}

        if request.method == 'POST':
            # Process the form submission to update assignments
            updated_assignments = request.form.getlist('assignments') # List of strings like 'user_id-greenhouse_id'

            # Clear existing assignments
            cursor.execute("DELETE FROM greenhouse_assignments")

            # Add the new assignments
            for assignment_str in updated_assignments:
                try:
                    user_id, greenhouse_id = map(int, assignment_str.split('-'))
                    cursor.execute("INSERT INTO greenhouse_assignments (user_id, greenhouse_id) VALUES (%s, %s)", (user_id, greenhouse_id))
                except ValueError:
                    flash('Invalid assignment data.', 'error')
                    conn.rollback()
                    return redirect(url_for('manage_assignments'))

            conn.commit()
            flash('Greenhouse assignments updated successfully.', 'success')
            return redirect(url_for('manage_assignments'))

        return render_template('manage_assignments.html', employees=employees, greenhouses=greenhouses, assignments=assignments)

    except Exception as e:
        app.logger.error(f"Error managing assignments: {e}")
        flash('An error occurred while managing greenhouse assignments.', 'error')
        return render_template('error.html')
    finally:
        if conn and conn.is_connected():
            conn.close()


@app.errorhandler(500)
def internal_error(error):
    return "An internal error occurred. Please try again later.", 500

# Assuming you have an alert_settings route defined like this:
@app.route('/alert_settings')
@require_role(['Manager'])
def alert_settings():
    # Your logic to handle the alert settings page
    return render_template('alert_settings.html')