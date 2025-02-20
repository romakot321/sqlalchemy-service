"""Module with database connection pool and engine"""
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase


logger.debug('Initialize service.base_db.base')

from sqlalchemy_service.base_db.db_configure import DBConfigurator


class ServiceEngine:
    def __init__(
            self,
            url: str | None = None,
            pool_size: int = 5,
            max_overflow: int = 0,
            pool_reset_on_return: bool = True,
            expire_on_commit: bool = False,
            autoflush: bool = True,
            autocommit: bool = False
    ):
        if url is None:
            db_configurator = DBConfigurator()
            url = db_configurator.configuration.get_url()

        self.engine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_reset_on_return=pool_reset_on_return
        )

        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession,
            expire_on_commit=expire_on_commit,
            autoflush=autoflush,
            autocommit=autocommit
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Generator for database session. Need to be closed"""
        async with self.async_session() as session:
            yield session

class Base(DeclarativeBase):
    pass

