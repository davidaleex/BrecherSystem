import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')

    # SQLite fallback for local development
    SQLITE_DATABASE_PATH = 'brecher_system.db'

    # Firebase configuration (Backend - Admin SDK)
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
    FIREBASE_AUTH_URI = os.environ.get('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth')
    FIREBASE_TOKEN_URI = os.environ.get('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token')

    # Firebase Web Configuration (Frontend)
    FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY')
    FIREBASE_WEB_AUTH_DOMAIN = os.environ.get('FIREBASE_WEB_AUTH_DOMAIN')
    FIREBASE_WEB_PROJECT_ID = os.environ.get('FIREBASE_WEB_PROJECT_ID', FIREBASE_PROJECT_ID)
    FIREBASE_WEB_STORAGE_BUCKET = os.environ.get('FIREBASE_WEB_STORAGE_BUCKET')
    FIREBASE_WEB_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_WEB_MESSAGING_SENDER_ID')
    FIREBASE_WEB_APP_ID = os.environ.get('FIREBASE_WEB_APP_ID')

    @property
    def use_postgresql(self):
        """Check if PostgreSQL should be used"""
        return bool(self.DATABASE_URL and self.DATABASE_URL.startswith('postgresql'))

    @property
    def database_config(self):
        """Get database configuration based on environment"""
        if self.use_postgresql:
            return {
                'type': 'postgresql',
                'url': self.DATABASE_URL
            }
        else:
            return {
                'type': 'sqlite',
                'path': self.SQLITE_DATABASE_PATH
            }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}