from backend.database import init_db

# Import all models to register them with Base
import backend.models

print("Initializing database with all models...")
init_db()
print("Database initialized successfully!")

