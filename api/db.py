import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get NeonDB URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a connection to NeonDB
def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        return None
