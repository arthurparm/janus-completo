"""
Configuração do banco de dados PostgreSQL para Configuration-as-Data.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.models.config_models import Base


class PostgresDatabase:
    """Gerenciador de conexão PostgreSQL para configurações dinâmicas."""

    def __init__(self):
        self._engine: Engine | None = None
        self._session_factory = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Inicializa o engine SQLAlchemy com configurações otimizadas."""
        postgres_url = (
            f"postgresql+psycopg2://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/"
            f"{settings.POSTGRES_DB}"
        )

        self._engine = create_engine(
            postgres_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
            echo=settings.ENVIRONMENT == "development",
        )

        self._session_factory = sessionmaker(bind=self._engine, autocommit=False, autoflush=False)

    @property
    def engine(self) -> Engine:
        """Retorna o engine SQLAlchemy."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        return self._engine

    def create_tables(self):
        """Cria todas as tabelas definidas nos modelos."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        Base.metadata.create_all(bind=self._engine)

    def drop_tables(self):
        """Remove todas as tabelas (usar com cuidado!)."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        Base.metadata.drop_all(bind=self._engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager para sessões de banco de dados."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """Retorna uma sessão direta (lembre-se de fechar!)."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")
        return self._session_factory()


# Instância singleton
postgres_db = PostgresDatabase()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency injection para FastAPI."""
    with postgres_db.get_session() as session:
        yield session


def init_database():
    """Inicializa o banco de dados PostgreSQL."""
    postgres_db.create_tables()
