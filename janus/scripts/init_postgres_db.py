import sys
import os
import time

# Ensure app path is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.postgres_config import postgres_db
from app.config import settings

def init_db():
    print(f"🐘 Initializing PostgreSQL database at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}...")
    
    # SQL Commands for Postgres
    commands = [
        # 1. Create Tables (Prompts)
        """
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            prompt_name VARCHAR(100) NOT NULL,
            prompt_version VARCHAR(20) NOT NULL DEFAULT '1.0',
            prompt_text TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            namespace VARCHAR(50) DEFAULT 'default',
            language VARCHAR(10) DEFAULT 'pt-BR',
            model_target VARCHAR(50) DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100) DEFAULT 'system',
            UNIQUE (prompt_name, namespace, is_active, language, model_target)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_prompt_lookup ON prompts (prompt_name, namespace, is_active);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_prompt_version ON prompts (prompt_name, prompt_version);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_active_prompts ON prompts (is_active, namespace);
        """,

        # 2. Create Enum Type (Safe)
        """
        DO $$ BEGIN
            CREATE TYPE priority_level_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """,

        # 3. Create Tables (Agent Configs)
        """
        CREATE TABLE IF NOT EXISTS agent_configurations (
            id SERIAL PRIMARY KEY,
            agent_name VARCHAR(100) NOT NULL,
            agent_role VARCHAR(50) NOT NULL,
            llm_provider VARCHAR(50) NOT NULL,
            llm_model VARCHAR(100) NOT NULL,
            prompt_id INT REFERENCES prompts(id) ON DELETE SET NULL,
            max_retries INT DEFAULT 3,
            timeout_seconds INT DEFAULT 60,
            temperature DECIMAL(3,2) DEFAULT 0.7,
            max_tokens INT DEFAULT 4096,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            priority_level priority_level_enum DEFAULT 'MEDIUM',
            cost_budget_usd DECIMAL(10,4) DEFAULT 0.05,
            performance_threshold DECIMAL(3,2) DEFAULT 0.8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100) DEFAULT 'system',
            UNIQUE (agent_name, agent_role, is_active)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_agent_lookup ON agent_configurations (agent_name, agent_role, is_active);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_agent_provider ON agent_configurations (llm_provider, llm_model);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_active_configs ON agent_configurations (is_active, agent_role);
        """,

        # 4. Optimization History
        """
        CREATE TABLE IF NOT EXISTS optimization_history (
            id SERIAL PRIMARY KEY,
            agent_config_id INT REFERENCES agent_configurations(id) ON DELETE SET NULL,
            metric_name VARCHAR(100) NOT NULL,
            old_value TEXT,
            new_value TEXT,
            reasoning TEXT,
            applied_by VARCHAR(100) DEFAULT 'meta-agent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # 5. Functions & Triggers
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
        """
        DROP TRIGGER IF EXISTS update_prompts_updated_at ON prompts;
        """,
        """
        CREATE TRIGGER update_prompts_updated_at
            BEFORE UPDATE ON prompts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """,
        """
        DROP TRIGGER IF EXISTS update_agent_configs_updated_at ON agent_configurations;
        """,
        """
        CREATE TRIGGER update_agent_configs_updated_at
            BEFORE UPDATE ON agent_configurations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    ]

    try:
        with postgres_db.get_session() as session:
            for i, cmd in enumerate(commands):
                print(f"Executing command {i+1}/{len(commands)}...")
                session.execute(text(cmd))
            session.commit()
            print("✅ Database initialization completed successfully!")
            
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
