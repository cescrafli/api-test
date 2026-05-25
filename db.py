from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from config import Config

# Initialize SQLAlchemy engine
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI, 
    pool_size=10, 
    max_overflow=20, 
    pool_recycle=3600
)

# Create a scoped session for thread safety
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_session():
    """Returns the database session."""
    return db_session

def close_session(exception=None):
    """Closes the database session."""
    db_session.remove()
