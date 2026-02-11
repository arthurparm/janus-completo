"""
Configuração do banco de dados PostgreSQL para Configuration-as-Data.
"""

from collections.abc import Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.models.config_models import Base
import app.models  # noqa: F401  # Ensures all models are registered before create_all


class PostgresDatabase:
    """Gerenciador de conexão PostgreSQL assíncrono para configurações dinâmicas."""

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory = None
        self._sync_engine = None
        self._sync_session_factory = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Inicializa o engine SQLAlchemy com driver asyncpg."""
        postgres_url = (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/"
            f"{settings.POSTGRES_DB}"
        )
        sync_driver = "psycopg2"
        try:
            import psycopg2  # noqa: F401
        except Exception:
            sync_driver = "psycopg"

        sync_url = (
            f"postgresql+{sync_driver}://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD.get_secret_value()}@"
            f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/"
            f"{settings.POSTGRES_DB}"
        )

        self._engine = create_async_engine(
            postgres_url,
            # poolclass=QueuePool,  # Removido para compatibilidade com AsyncIO
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            echo=settings.ENVIRONMENT == "development",
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        self._sync_engine = create_engine(
            sync_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            echo=settings.ENVIRONMENT == "development",
        )
        self._sync_session_factory = sessionmaker(
            bind=self._sync_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Retorna o engine SQLAlchemy assíncrono."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        return self._engine

    async def create_tables(self):
        """Cria todas as tabelas definidas nos modelos (assíncrono)."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Remove todas as tabelas (usar com cuidado!)."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
            
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        [DEPRECATED] Interface síncrona mantida para compatibilidade temporária.
        Prefira usar get_session_async.
        """
        if self._sync_session_factory is None:
            raise RuntimeError("Sync session factory not initialized")
        session: Session = self._sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """Retorna sessao sync para compatibilidade com repositorios legados."""
        if self._sync_session_factory is None:
            raise RuntimeError("Sync session factory not initialized")
        return self._sync_session_factory()

    @asynccontextmanager
    async def get_session_async(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager para sessões de banco de dados assíncronas."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")
        
        session: AsyncSession = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Instância singleton
postgres_db = PostgresDatabase()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection para FastAPI (Async)."""
    async with postgres_db.get_session_async() as session:
        yield session


async def init_database():
    """Inicializa o banco de dados PostgreSQL."""
    await postgres_db.create_tables()
