"""Module with database connection pool and engine"""

import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

logger.debug('Initialize service.base_db.base')

from sqlalchemy_service.base_db.db_configure import DBConfigurator

db_configurator = DBConfigurator()
DATABASE_URL = db_configurator.configuration.get_url()

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=0,
    pool_reset_on_return=True,
)


class Base(DeclarativeBase):
    pass


async_session = sessionmaker(
    engine, class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


async def init_models():
    """Migrate models to DB. Better to use alembic"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info('Models initialisation is done')


def run_init_models():
    asyncio.run(init_models())


async def get_session():
    """Generator for database session. Need to be closed"""
    async with async_session() as session:
        yield session


if __name__ == "__main__":
    run_init_models()
