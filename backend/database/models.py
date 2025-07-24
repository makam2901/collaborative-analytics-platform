from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    """
    Represents the User table in the database.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    hashed_password: str

class UserCreate(SQLModel):
    username: str
    email: str
    password: str
