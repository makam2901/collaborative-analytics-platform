from typing import List, Optional
from enum import Enum
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    """Represents the User table in the database."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    hashed_password: str

    projects: List["Project"] = Relationship(back_populates="owner")


class Project(SQLModel, table=True):
    """Represents the Project table."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="projects")

    datasets: List["Dataset"] = Relationship(back_populates="project")


class Dataset(SQLModel, table=True):
    """Represents the Dataset table."""
    id: Optional[int] = Field(default=None, primary_key=True)
    file_name: str
    file_path: str
    description: Optional[str] = None
    table_name: str = Field(index=True) 

    project_id: int = Field(foreign_key="project.id")
    project: Project = Relationship(back_populates="datasets")


class UserCreate(SQLModel):
    username: str
    email: str
    password: str

# --- New Models for Project and Dataset ---

class ProjectCreate(SQLModel):
    """Data model for creating a new project."""
    name: str
    description: Optional[str] = None


class ProjectRead(SQLModel):
    """Data model for reading a project."""
    id: int
    name: str
    description: Optional[str]
    owner_id: int

class QueryLanguage(str, Enum):
    python = "python"
    sql = "sql"

class QueryRequest(SQLModel):
    """Data model for a user's natural language query."""
    question: str
    language: QueryLanguage = QueryLanguage.python
    provider: Optional[str] = "gemini"
    model: Optional[str] = "gemini-1.5-flash"

class DatasetRead(SQLModel):
    id: int
    file_name: str
    description: Optional[str]
    table_name: str

class ProjectReadWithDatasets(ProjectRead):
    datasets: List[DatasetRead] = []

class CodeExecutionRequest(SQLModel):
    code: str
    language: QueryLanguage
    provider: Optional[str] = "gemini"
    model: Optional[str] = "gemini-1.5-flash"