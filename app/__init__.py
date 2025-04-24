from flask import Flask
from flask_wtf.csrf import CSRFProtect
from .config import Config
from flask_login import LoginManager
from .utils.db_utils import init_db, load_user
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.user_loader(load_user)

try:
    # Initialize services
    app.twilio_client = Config.init_twilio()
    init_db(app)
except Exception as e:
    logging.error(f"Failed to initialize application: {str(e)}")
    raise

# Import routes after app is fully configured to avoid circular imports
from . import routes