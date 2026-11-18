"""
Configuracao do banco de dados PostgreSQL para Configuration-as-Data.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import app.models  # noqa: F401  # Ensures all models are registered before create_all
import structlog
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.config_models import Base

logger = structlog.get_logger(__name__)


class PostgresDatabase:
    """Gerenciador de conexao PostgreSQL assincrono para configuracoes dinamicas."""

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory = None
        self._sync_engine = None
        self._sync_session_factory = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._initialize_engine()
        self._initialized = True

    def _initialize_engine(self) -> None:
        """Inicializa os engines SQLAlchemy apenas quando necessario."""
        if self._engine is not None or self._sync_engine is not None:
            return

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
        self._ensure_initialized()
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        return self._engine

    async def create_tables(self) -> None:
        self._ensure_initialized()
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        self._ensure_initialized()
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def shutdown(self) -> None:
        async_engine = self._engine
        sync_engine = self._sync_engine

        self._engine = None
        self._sync_engine = None
        self._session_factory = None
        self._sync_session_factory = None
        self._initialized = False

        if async_engine is not None:
            try:
                await asyncio.shield(async_engine.dispose())
            except asyncio.CancelledError:
                logger.warning("Database async engine dispose cancelled during shutdown")
            except Exception as e:
                logger.warning("Failed to dispose async database engine", exc_info=e)

        if sync_engine is not None:
            try:
                sync_engine.dispose()
            except Exception as e:
                logger.warning("Failed to dispose sync database engine", exc_info=e)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        self._ensure_initialized()
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
        self._ensure_initialized()
        if self._sync_session_factory is None:
            raise RuntimeError("Sync session factory not initialized")
        return self._sync_session_factory()

    @asynccontextmanager
    async def get_session_async(self) -> AsyncGenerator[AsyncSession, None]:
        self._ensure_initialized()
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


# Instancia singleton
postgres_db = PostgresDatabase()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with postgres_db.get_session_async() as session:
        yield session


async def init_database() -> None:
    await postgres_db.create_tables()


async def shutdown_database() -> None:
    await postgres_db.shutdown()
