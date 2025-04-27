import os
from warnings import warn
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables from .env file first
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'greenhouse_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE', 5))

    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

    @classmethod
    def validate(cls):
        """Check critical config before app starts"""
        if cls.SECRET_KEY.startswith('dev-only'):
            warn('Using development SECRET_KEY! Change in production!', RuntimeWarning)

        if not all([cls.MYSQL_USER, cls.MYSQL_DB]):
            raise ValueError("MySQL configuration incomplete")

        if not cls.MYSQL_PASSWORD:
            warn('MySQL password not set', RuntimeWarning)

        if not all([cls.TWILIO_ACCOUNT_SID, cls.TWILIO_AUTH_TOKEN, cls.TWILIO_PHONE_NUMBER]):
            warn('Twilio configuration incomplete - SMS features will be disabled', RuntimeWarning)

    @classmethod
    def init_twilio(cls):
        """Initialize Twilio client if credentials exist"""
        if all([cls.TWILIO_ACCOUNT_SID, cls.TWILIO_AUTH_TOKEN]):
            return Client(cls.TWILIO_ACCOUNT_SID, cls.TWILIO_AUTH_TOKEN)
        return None
