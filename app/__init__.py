from flask import Flask
from .config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize DB
from .utils.db_utils import init_db
init_db(app)

# Import routes AFTER app exists
from . import routes