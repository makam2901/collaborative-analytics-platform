from sqlmodel import create_engine, Session, SQLModel
from config import DATABASE_URL

# The engine is the entry point to the database.
# connect_args is needed for SQLite, but we keep it here for compatibility.
engine = None

def get_session():
    """
    Dependency function to get a new database session for each request.
    """
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """
    Utility function to create all database tables.
    Called once on application startup.
    """
    SQLModel.metadata.create_all(engine)
