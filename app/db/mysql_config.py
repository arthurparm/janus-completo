"""
Configuração do banco de dados MySQL para Configuration-as-Data.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.models.config_models import Base


class MySQLDatabase:
    """Gerenciador de conexão MySQL para configurações dinâmicas."""

    def __init__(self):
        self._engine: Engine = None
        self._session_factory = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Inicializa o engine SQLAlchemy com configurações otimizadas."""
        mysql_url = (
            f"mysql+pymysql://{settings.MYSQL_USER}:"
            f"{settings.MYSQL_PASSWORD.get_secret_value()}@"
            f"{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/"
            f"{settings.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

        self._engine = create_engine(
            mysql_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.ENVIRONMENT == "development"
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False
        )

    @property
    def engine(self) -> Engine:
        """Retorna o engine SQLAlchemy."""
        return self._engine

    def create_tables(self):
        """Cria todas as tabelas definidas nos modelos."""
        Base.metadata.create_all(bind=self._engine)

    def drop_tables(self):
        """Remove todas as tabelas (usar com cuidado!)."""
        Base.metadata.drop_all(bind=self._engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager para sessões de banco de dados."""
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
        return self._session_factory()


# Instância singleton
mysql_db = MySQLDatabase()


def get_mysql_session() -> Generator[Session, None, None]:
    """Dependency injection para FastAPI."""
    with mysql_db.get_session() as session:
        yield session


def init_mysql_database():
    """Inicializa o banco de dados MySQL."""
    mysql_db.create_tables()
