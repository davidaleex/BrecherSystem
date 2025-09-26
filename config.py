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