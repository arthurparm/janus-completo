from app.db.postgres_config import postgres_db, get_db_session

# Alias generic 'db' to the specific implementation
db = postgres_db
