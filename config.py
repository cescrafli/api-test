import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    
    # Database configurations
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_USER = os.environ.get('DB_USER', 'user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'pass')
    DB_NAME = os.environ.get('DB_NAME', 'db')
    
    # Construct SQLAlchemy Database URI (using PyMySQL for MySQL)
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Swagger UI Configurations
    RESTX_MASK_SWAGGER = False
