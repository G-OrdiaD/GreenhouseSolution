import os
from dotenv import load_dotenv
from warnings import warn

# Load environment variables from .env file
load_dotenv()

class Config:
    # Security (Required)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-fallback-key'

    # Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'greenhouse_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE', 5))

    # Validation
    @classmethod
    def validate(cls):
        """Check critical config before app starts"""
        if cls.SECRET_KEY.startswith('dev-only'):
            warn('Using development SECRET_KEY! Change in production!', RuntimeWarning)

        if not all([cls.MYSQL_USER, cls.MYSQL_DB]):
            raise ValueError("MySQL configuration incomplete")

        if not cls.MYSQL_PASSWORD:
            warn('MySQL password not set', RuntimeWarning)