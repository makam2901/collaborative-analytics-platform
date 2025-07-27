from fastapi import UploadFile, File, Form
from database.models import ProjectReadWithDatasets
from database.models import CodeExecutionRequest

import pandas as pd
from database.models import QueryRequest, QueryLanguage
from llm_service import get_user_intent, generate_aggregation_code, generate_visualization_code
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

# In main.py, replace the entire query_project function
@app.post("/api/projects/{project_id}/query")
def query_project(
    project_id: int,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    datasets = project.datasets
    if not datasets:
        raise HTTPException(status_code=400, detail="No datasets to query.")

    intent = get_user_intent(request.question)
    
    tables_context = []
    code_preamble = ["import pandas as pd", "from pandasql import sqldf", "import plotly.express as px"]
    for ds in datasets:
        try:
            df_head = pd.read_csv(ds.file_path, nrows=5)
            tables_context.append({"table_name": ds.table_name, "variable_name": f"{ds.table_name}_df", "description": ds.description, "columns": df_head.columns.tolist()})
            # This line correctly prepares the command to load the dataframe in the kernel
            code_preamble.append(f"{ds.table_name}_df = pd.read_csv(r'{ds.file_path}')")
        except Exception as e:
            print(f"Could not read or process {ds.file_name}: {e}")
            continue

    aggregation_code = generate_aggregation_code(
        question=request.question,
        tables_context=tables_context,
        language=request.language
    )
    
    preamble_str = "\n".join(code_preamble)
    
    if request.language == "sql":
        sql_env_str_list = [f"'{tbl['table_name']}': {tbl['variable_name']}" for tbl in tables_context]
        sql_env_str = "{" + ", ".join(sql_env_str_list) + "}"
        clean_agg_code = aggregation_code.replace("'''", "''")
        # The final 'agg_df' variable is crucial for the visualization step
        full_agg_code = f"{preamble_str}\npysqldf = lambda q: sqldf(q, {sql_env_str})\nsql_query = '''{clean_agg_code}'''\nagg_df = pysqldf(sql_query)\nprint(agg_df.to_string())"
    else: # Python
        # THIS IS THE FIX: The aggregation_code is assigned to 'agg_df'
        full_agg_code = f"{preamble_str}\nagg_df = {aggregation_code}\nprint(agg_df.to_string())"
    
    aggregation_results = execute_code_in_kernel(full_agg_code)

    plot_json = None
    if intent == 'chart':
        agg_result_text = ""
        for result in reversed(aggregation_results):
            if result.get('text', '').strip():
                agg_result_text = result['text']
                break
        
        if agg_result_text:
            viz_code = generate_visualization_code(request.question, agg_result_text)
            # The visualization code runs in an environment where 'agg_df' already exists
            viz_preamble = full_agg_code.split('print')[0]
            full_viz_code = f"{viz_preamble}\n{viz_code}"
            viz_results = execute_code_in_kernel(full_viz_code)
            
            if viz_results:
                last_result = viz_results[-1]
                if last_result['type'] == 'result' and last_result['text'].strip().startswith('{'):
                    plot_json = last_result['text']
    
    return {
        "language": request.language,
        "aggregation_code": aggregation_code,
        "aggregation_results": aggregation_results,
        "plot_json": plot_json,
    }

@app.get("/api/projects/{project_id}", response_model=ProjectReadWithDatasets)
def read_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Retrieve a single project and its datasets, ensuring it belongs to the current user.
    """
    # This query robustly checks for both the project ID and the correct owner
    statement = select(Project).where(
        Project.id == project_id,
        Project.owner_id == current_user.id
    )
    project = session.exec(statement).first()

    # If the query returns nothing, the project either doesn't exist
    # or doesn't belong to this user, so we raise a 404.
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return project

@app.post("/api/projects/{project_id}/run-code")
def run_code(
    project_id: int,
    request: CodeExecutionRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    datasets = project.datasets
    if not datasets:
        raise HTTPException(status_code=400, detail="No datasets in this project to query.")

    code_preamble = ["import pandas as pd", "from pandasql import sqldf", "import plotly.express as px"]
    for ds in datasets:
        code_preamble.append(f"{ds.table_name}_df = pd.read_csv(r'{ds.file_path}')")
    preamble_str = "\n".join(code_preamble)
    
    if request.language == "sql":
        sql_env_str_list = [f"'{ds.table_name}': {ds.table_name}_df" for ds in datasets]
        sql_env_str = "{" + ", ".join(sql_env_str_list) + "}"
        clean_request_code = request.code.replace("'''", "''")

        full_code_to_execute = f"""
{preamble_str}
pysqldf = lambda q: sqldf(q, {sql_env_str})
sql_query = '''{clean_request_code}'''
result = pysqldf(sql_query)
print(result)
"""
    else: # Python
        full_code_to_execute = f"{preamble_str}\n{request.code}"
    
    execution_results = execute_code_in_kernel(full_code_to_execute)
    
    if execution_results:
        last_result = execution_results[-1]
        if last_result['type'] == 'result' and last_result['text'].strip().startswith('{'):
            try:
                plot_json = last_result['text']
                execution_results[-1] = {'type': 'plotly_json', 'data': plot_json}
            except Exception:
                pass

    return {"execution_results": execution_results}