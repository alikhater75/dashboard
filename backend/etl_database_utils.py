
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base  # Import the Base from your existing file
from dotenv import load_dotenv
load_dotenv()



def get_engine():
    """Returns a SQLAlchemy engine for our PostgreSQL database."""
    # Build the connection string from Streamlit's secrets
    db_url = os.environ.get("DATABASE_URL")
    SYNC_DATABASE_URL = db_url.replace("+asyncpg", "")
    if SYNC_DATABASE_URL is None:
        raise ValueError("DATABASE_URL environment variable is not set.")
    
    return create_engine(SYNC_DATABASE_URL)

def create_database_and_tables():
    """Creates all defined tables in the PostgreSQL database if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database setup complete. Connected to PostgreSQL.")

def get_session():
    """Returns a new session to interact with the database."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
