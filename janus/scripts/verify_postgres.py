import sys
import os

# Ensure app path is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.postgres_config import postgres_db
from app.config import settings

def test_postgres_connection():
    print(f"🐘 Testing PostgreSQL connection to {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} as {settings.POSTGRES_USER}...")
    try:
        with postgres_db.get_session() as session:
            # 1. Basic Connection
            result = session.execute(text("SELECT version();")).scalar()
            print(f"✅ Connection Successful! Version: {result}")

            # 2. Check pgvector extension
            print("🔍 Checking pgvector extension...")
            extensions = session.execute(text("SELECT extname FROM pg_extension;")).fetchall()
            ext_names = [r[0] for r in extensions]
            if "vector" in ext_names:
                print("✅ pgvector extension is installed.")
            else:
                print("⚠️ pgvector extension NOT found (it might be installed but not enabled in this DB).")
                # Attempt to enable
                try:
                    session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    session.commit()
                    print("✅ pgvector extension enabled successfully.")
                except Exception as e:
                    print(f"❌ Failed to enable pgvector: {e}")

            # 3. Check JSONB table creation (Simulated via Model or Raw SQL)
            print("📝 Verifying JSONB capability...")
            try:
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS verification_test (
                        id SERIAL PRIMARY KEY,
                        data JSONB
                    );
                """))
                session.execute(text("INSERT INTO verification_test (data) VALUES ('{\"test\": true, \"value\": 123}')"))
                session.commit()
                row = session.execute(text("SELECT data FROM verification_test LIMIT 1;")).scalar()
                print(f"✅ JSONB Test Passed: Retrieved {row}")
                # Cleanup
                session.execute(text("DROP TABLE verification_test;"))
                session.commit()
            except Exception as e:
                print(f"❌ JSONB Test Failed: {e}")
                
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_postgres_connection()
