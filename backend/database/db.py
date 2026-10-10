"""
Async SQLAlchemy engine/session setup + pgvector registration.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_async_engine(settings.database_url, echo=(settings.env == "development"), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency yielding an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create the pgvector extension and all tables. Called on startup."""
    from sqlalchemy import text
    import models.orm_models       # noqa: F401 register models with Base
    import models.patient_profile  # noqa: F401 register PatientProfile table
    import models.user             # noqa: F401 register User table

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully (pgvector extension + tables ensured).")
    except Exception as exc:
        logger.warning(
            "Database connection failed during startup (%s).\n"
            "Ensure PostgreSQL is running on %s with the 'pgvector' extension installed,\n"
            "and that the 'policygraph' database exists. (Run: createdb -U postgres policygraph)",
            exc,
            settings.database_url,
        )
