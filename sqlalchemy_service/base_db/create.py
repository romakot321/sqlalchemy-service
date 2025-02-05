"""Module with functions for prepare database for using"""

import asyncio
import os

try:
    import asyncpg as driver
except ImportError:
    driver = None

from loguru import logger
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    database_host: str = os.getenv('database_host')
    database_db: str = os.getenv('database_db')
    database_password: str = os.getenv('database_password')
    database_user: str = os.getenv('database_user')
    database_type: str = os.getenv('database_type', "postgres")
    database_driver: str | None = os.getenv('database_driver', "asyncpg")


settings = Settings()


async def connect_create_if_not_exists(user, database, password, host):
    """Do a 20 attempts to connect and create database"""
    for i in range(20):
        try:
            conn = await driver.connect(
                user=user, database=database,
                password=password, host=host
            )
            await conn.close()
            break
        except driver.InvalidCatalogNameError:
            # Database does not exist, create it.
            sys_conn = await driver.connect(
                database='template1',
                user=user,
                password=password,
                host=host
            )
            await sys_conn.execute(
                f'CREATE DATABASE "{database}" OWNER "{user}"'
            )
            await sys_conn.close()
            break
        except Exception as e:
            logger.exception(f"Error on database connection: {str(e)}\n[{i + 1}/20] Retry in 5 seconds...")
            await asyncio.sleep(5)


def run_init_db():
    """Run database creation in DMS. Use provided driver_name for driver import"""
    global driver
    if settings.database_driver:
        driver = __import__(settings.database_driver)

    asyncio.run(
        connect_create_if_not_exists(
            settings.database_user,
            settings.database_db,
            settings.database_password,
            settings.database_host
        )
    )
    logger.info(f'DB initialization with name {settings.database_db} is done')


if __name__ == '__main__':
    run_init_db()
