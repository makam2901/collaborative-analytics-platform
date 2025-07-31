# Standard Library Imports
import os
import re
import shutil
from contextlib import asynccontextmanager
from datetime import timedelta

# Third-Party Library Imports
import pandas as pd
from sqlmodel import Session, create_engine, select

from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, UploadFile, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

# Configuration and Core Setup
from config import DATABASE_URL

# Authentication Logic
from auth import (
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token,
    get_password_hash, verify_password
)

# Database Layer
from sqlmodel import SQLModel, create_engine
import database.db as db
from database.db import get_session
from database.models import (
    User, UserCreate,
    Project, ProjectCreate, ProjectRead, ProjectReadWithDatasets,
    Dataset,
    QueryRequest, QueryLanguage,
    VisualizationRequest, CodeExecutionRequest
)

# LLM & Notebook Services
from llm_service import generate_aggregation_code, generate_visualization_code
from notebook_runner import execute_code_in_kernel

def get_kernel_output_as_json(results: list) -> str:
    """Finds the last text output from the kernel and returns it."""
    text_output = ""
    # Look for the last non-empty text result from the kernel
    for result in reversed(results):
        if result.get('text', '').strip():
            text_output = result['text'].strip()
            break
    return text_output

def to_snake_case(name: str) -> str:
    """Converts a string to snake_case and removes file extension."""
    s = os.path.splitext(name)[0]  # Remove file extension
    s = re.sub(r'[\s-]+', '_', s)    # Replace spaces and hyphens with underscores
    s = re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower() # Handle CamelCase
    return re.sub(r'[^a-zA-Z0-9_]', '', s) # Remove invalid characters

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs when the application starts up.
    It creates the database connection and then the tables.
    """
    print("Creating database engine...")
    
    engine = create_engine(DATABASE_URL, echo=True) 
    db.engine = engine
    SQLModel.metadata.create_all(engine)
    
    yield
    
    print("Database engine closed.")


# Initialize FastAPI app with the corrected lifespan manager
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
        raise HTTPException(status_code=400, detail="No datasets in this project to query.")

    tables_context = []
    code_preamble = ["import pandas as pd", "from pandasql import sqldf"]
    for ds in datasets:
        try:
            df = pd.read_csv(ds.file_path)
            columns_with_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
            tables_context.append({
                "table_name": ds.table_name, "variable_name": f"{ds.table_name}_df",
                "description": ds.description, "columns_with_types": columns_with_types
            })
            code_preamble.append(f"{ds.table_name}_df = pd.read_csv(r'{ds.file_path}')")
        except Exception as e:
            print(f"Could not read or process {ds.file_name}: {e}")
            continue

    aggregation_code = generate_aggregation_code(
        question=request.question, tables_context=tables_context, language=request.language, provider=request.provider, model=request.model
    )
    
    preamble_str = "\n".join(code_preamble)
    if request.language == "sql":
        sql_env_str_list = [f"'{tbl['table_name']}': {tbl['variable_name']}" for tbl in tables_context]
        sql_env_str = "{" + ", ".join(sql_env_str_list) + "}"
        clean_agg_code = aggregation_code.replace("'''", "''")
        full_agg_code = f"{preamble_str}\npysqldf = lambda q: sqldf(q, {sql_env_str})\nsql_query = '''{clean_agg_code}'''\nans_df = pysqldf(sql_query)"
    else: # Python
        full_agg_code = f"{preamble_str}\n{aggregation_code}"

    # Execute and convert the final ans_df to JSON
    code_to_get_json = f"{full_agg_code}\nprint(ans_df.to_json(orient='records'))"
    execution_results = execute_code_in_kernel(code_to_get_json)

    # Extract the JSON data from the last output
    json_result_str = get_kernel_output_as_json(execution_results)
    
    # Check for errors from the kernel
    error_output = next((res for res in execution_results if res['type'] == 'error'), None)
    if error_output:
        raise HTTPException(status_code=400, detail=f"Error executing code: {error_output['evalue']}")

    return {
        "language": request.language,
        "aggregation_code": aggregation_code,
        "datatable_json": json_result_str, # Send the structured data
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
    """
    Executes a given block of user-edited code and returns the structured
    data table as JSON, plus an optional chart.
    """
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
    
    # Split the user's code to see if it contains a chart part
    aggregation_code = request.code
    visualization_code = None
    if "###CHART_CODE###" in request.code:
        parts = request.code.split("###CHART_CODE###")
        aggregation_code = parts[0].strip()
        visualization_code = parts[1].strip()

    # Always execute the aggregation part to get the data table
    if request.language == "sql":
        sql_env_str_list = [f"'{ds.table_name}': {ds.table_name}_df" for ds in datasets]
        sql_env_str = "{" + ", ".join(sql_env_str_list) + "}"
        clean_agg_code = aggregation_code.replace("'''", "''")
        full_agg_code = f"{preamble_str}\npysqldf = lambda q: sqldf(q, {sql_env_str})\nsql_query = '''{clean_agg_code}'''\nans_df = pysqldf(sql_query)"
    else: # Python
        full_agg_code = f"{preamble_str}\n{aggregation_code}"

    # --- THIS IS THE FIX ---
    # We now execute the code and explicitly print the final ans_df as JSON
    code_to_get_json = f"{full_agg_code}\nprint(ans_df.to_json(orient='records'))"
    aggregation_results = execute_code_in_kernel(code_to_get_json)
    datatable_json = get_kernel_output_as_json(aggregation_results)

    # If there was chart code, execute it to get the plot
    plot_json = None
    if visualization_code:
        viz_preamble = f"{preamble_str}\n{aggregation_code}"
        full_viz_code = f"{viz_preamble}\n{visualization_code}"
        viz_results = execute_code_in_kernel(full_viz_code)
        
        if viz_results:
            last_result = viz_results[-1]
            if last_result.get('type') == 'result' and last_result.get('text', '').strip().startswith('{'):
                plot_json = last_result['text']

    # Check for kernel errors
    error_output = next((res for res in aggregation_results if res['type'] == 'error'), None)
    if error_output:
        raise HTTPException(status_code=400, detail=f"Error executing code: {error_output['evalue']}")

    return {
        "language": request.language,
        "aggregation_code": request.code,
        "datatable_json": datatable_json,
        "plot_json": plot_json
    }


@app.post("/api/projects/{project_id}/visualize")
def visualize_data(
    project_id: int,
    request: VisualizationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate the visualization code
    viz_code = generate_visualization_code(request.dict(), request.provider, request.model)

    # Prepare the environment for execution
    # We load the full data table (ans_df) from the JSON sent by the frontend
    code_preamble = [
        "import pandas as pd",
        "import plotly.express as px",
        f"ans_df = pd.read_json('''{request.datatable_json}''', orient='records')"
    ]
    preamble_str = "\n".join(code_preamble)
    full_viz_code = f"{preamble_str}\n{viz_code}"
    
    viz_results = execute_code_in_kernel(full_viz_code)
    
    plot_json_result = next((res for res in viz_results if res['type'] == 'json_result'), None)
    plot_json = plot_json_result['text'] if plot_json_result else None

    error_output = next((res for res in viz_results if res['type'] == 'error'), None)
    if error_output:
        raise HTTPException(status_code=400, detail=f"Error visualizing data: {error_output['evalue']}")

    return {"plot_json": plot_json, "visualization_code": viz_code}