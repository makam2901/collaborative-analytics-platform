from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from contextlib import asynccontextmanager

from database.db import get_session, create_db_and_tables
from database.models import User

# Lifespan manager to create DB tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables...")
    create_db_and_tables()
    yield
    print("Tables created.")

# Initialize the FastAPI app with the lifespan manager
app = FastAPI(
    title="Collaborative Analytics Platform API",
    lifespan=lifespan
)

# CORS Middleware Configuration
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/api")
def read_root():
    """A simple endpoint to confirm the API is running."""
    return {"message": "Hello from the FastAPI Backend! 🚀"}

@app.post("/api/users/", response_model=User)
def create_user(user: User, session: Session = Depends(get_session)):
    """
    Create a new user and add it to the database.
    (Note: In a real app, we would hash the password)
    """
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/api/users/", response_model=list[User])
def read_users(session: Session = Depends(get_session)):
    """
    Retrieve all users from the database.
    """
    users = session.query(User).all()
    return users
