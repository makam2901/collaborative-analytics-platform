from fastapi import UploadFile, File, Form

import pandas as pd
from database.models import QueryRequest
from llm_service import generate_code
from notebook_runner import execute_code_in_kernel

from fastapi import UploadFile, File
import shutil
import os
from database.models import Dataset

from database.models import Project, ProjectCreate, ProjectRead
from auth import get_current_user
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from auth import (ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token,
                  get_password_hash, verify_password)
from database.db import create_db_and_tables, get_session
from database.models import User, UserCreate

import re

def to_snake_case(name: str) -> str:
    """Converts a string to snake_case and removes file extension."""
    s = os.path.splitext(name)[0]  # Remove file extension
    s = re.sub(r'[\s-]+', '_', s)    # Replace spaces and hyphens with underscores
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower() # Handle CamelCase
    return re.sub(r'[^a-zA-Z0-9_]', '', s) # Remove invalid characters

# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables...")
    create_db_and_tables()
    yield
    print("Tables created.")


# Initialize FastAPI app
app = FastAPI(title="Collaborative Analytics Platform API", lifespan=lifespan)

# CORS Middleware
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
    """A simple endpoint for health checks."""
    return {"status": "ok"}

@app.post("/api/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """
    Standard OAuth2 endpoint to log in a user and get an access token.
    """
    # Use select() for modern SQLModel/SQLAlchemy
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/users/", response_model=User)
def create_user(user_create: UserCreate, session: Session = Depends(get_session)):
    """
    Create a new user. The password will be hashed before storing.
    """
    hashed_password = get_password_hash(user_create.password)
    user = User(
        username=user_create.username,
        email=user_create.email,
        hashed_password=hashed_password,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/api/users/", response_model=list[User])
def read_users(session: Session = Depends(get_session)):
    """
    Retrieve all users from the database.
    (This should be a protected endpoint in a real app).
    """
    users = session.exec(select(User)).all()
    return users

@app.get("/api/users/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the data for the currently authenticated user.
    """
    return current_user

@app.post("/api/projects/", response_model=ProjectRead)
def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Create a new project for the currently authenticated user.
    """
    # Create a new Project instance, linking it to the current user
    new_project = Project.from_orm(project, update={'owner_id': current_user.id})
    
    session.add(new_project)
    session.commit()
    session.refresh(new_project)
    return new_project

@app.get("/api/projects/", response_model=list[ProjectRead])
def read_projects(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Retrieve all projects owned by the currently authenticated user.
    """
    projects = session.exec(select(Project).where(Project.owner_id == current_user.id)).all()
    return projects

# Define the upload directory
UPLOAD_DIRECTORY = "/app/uploads"

@app.post("/api/projects/{project_id}/upload-dataset/", response_model=Dataset)
def upload_dataset(
    project_id: int,
    file: UploadFile = File(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload a dataset, generating a clean table_name for LLM use.
    """
    # Verify the project exists and belongs to the current user
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate a clean table name from the filename
    clean_table_name = to_snake_case(file.filename)

    # Define the file path and save the file
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create a new Dataset record in the database
    new_dataset = Dataset(
        file_name=file.filename,
        file_path=file_path,
        description=description,
        table_name=clean_table_name,  # Save the clean name
        project_id=project.id,
    )
    session.add(new_dataset)
    session.commit()
    session.refresh(new_dataset)
    
    return new_dataset

# Remove the old query_dataset function and replace it with this one.

@app.post("/api/projects/{project_id}/query")
def query_project(
    project_id: int,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Takes a natural language question about a project, generates code
    using the context of all datasets in that project, executes it,
    and returns the code and result.
    """
    # 1. Verify ownership and fetch the project
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Get all datasets associated with the project
    datasets = project.datasets
    if not datasets:
        raise HTTPException(status_code=400, detail="No datasets in this project to query.")

    # 3. Prepare the multi-table context for the LLM
    tables_context = []
    code_preamble = ["import pandas as pd", "from pandasql import sqldf"]

    for ds in datasets:
        try:
            df_head = pd.read_csv(ds.file_path, nrows=5)
            # Use the clean table_name for variable names
            df_variable_name = f"{ds.table_name}_df"
            code_preamble.append(f"{df_variable_name} = pd.read_csv('{ds.file_path}')")
            
            tables_context.append({
                "table_name": ds.table_name,
                "variable_name": df_variable_name,
                "description": ds.description,
                "columns": df_head.columns.tolist(),
                "head": df_head.to_string()
            })
        except Exception as e:
            # Silently skip files that can't be read, or handle more gracefully
            print(f"Could not read or process {ds.file_name}: {e}")
            continue
    
    # 4. Generate code using the LLM with the full context
    generated_code = generate_code(
        question=request.question,
        tables_context=tables_context,
        language=request.language
    )

    # 5. Prepare the full code for execution
    if request.language == "python":
        # The preamble already loads the dataframes
        full_code_to_execute = "\n".join(code_preamble) + f"\n{generated_code}"
    elif request.language == "sql":
        # The SQL query will reference table names, pandasql will find them in globals()
        # We still need the preamble to load the dataframes
        sql_preamble = "\n".join(code_preamble)
        full_code_to_execute = f"""
{sql_preamble}
pysqldf = lambda q: sqldf(q, globals())
sql_query = '''{generated_code.replace("'''", "''")}'''
result = pysqldf(sql_query)
print(result)
"""
    
    # 6. Execute the code
    execution_results = execute_code_in_kernel(full_code_to_execute)

    # 7. Return the response
    return {
        "language": request.language,
        "generated_code": generated_code,
        "execution_results": execution_results,
    }
