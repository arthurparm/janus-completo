from app.db.postgres_config import get_db_session, postgres_db

# Alias generic 'db' to the specific implementation
db = postgres_db
