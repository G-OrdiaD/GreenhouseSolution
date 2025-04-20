from flask import Flask
from .config import Config
import sys

app = Flask(__name__)
app.config.from_object(Config)

# Only initialize DB if not running unit tests
if not ('unittest' in sys.modules or 'pytest' in sys.modules):
    from .utils.db_utils import init_db
    init_db(app)

# Import routes AFTER app exists
from . import routes
