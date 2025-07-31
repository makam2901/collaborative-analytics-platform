from sqlmodel import Session

# The engine will be created and managed entirely by main.py
engine = None

def get_session():
    """
    Dependency function to get a new database session for each request.
    It relies on the 'engine' being set by the main app's lifespan.
    """
    with Session(engine) as session:
        yield session