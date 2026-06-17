"""
Configuration and environment variables.
Loads settings from .env file and provides defaults.
"""

import os
from dotenv import load_dotenv

# Load from backend/.env first, then root .env
load_dotenv('backend/.env')
load_dotenv()

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./cpa.db"
)

# FastAPI
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "your-secret-key-change-in-production"
)

# Server
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# File upload
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))  # 50MB

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Features
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

print(f"✅ Configuration loaded")
print(f"   Debug mode: {DEBUG}")
# Extract database info
if "sqlite" in DATABASE_URL:
    db_info = f"SQLite - {DATABASE_URL.replace('sqlite:///', '')}"
elif "@" in DATABASE_URL:
    db_info = DATABASE_URL.split('@')[1]
else:
    db_info = DATABASE_URL
print(f"   Database: {db_info}")
