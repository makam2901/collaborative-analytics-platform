import os
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

