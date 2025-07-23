i
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize the FastAPI app
app = FastAPI(title="Collaborative Analytics Platform API")

# Configure CORS (Cross-Origin Resource Sharing)
# This allows our React frontend (running on http://localhost:3000)
# to make requests to our backend (running on http://localhost:8000).
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define a root endpoint
@app.get("/api")
def read_root():
    """A simple endpoint to confirm the API is running."""
    return {"message": "Hello from the FastAPI Backend! 🚀"}

