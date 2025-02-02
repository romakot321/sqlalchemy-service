"""Module with functions for prepare database for using"""

import asyncio
import os

import asyncpg
from loguru import logger
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    postgres_host: str = os.getenv('postgres_host')
    postgres_db: str = os.getenv('postgres_db')
    postgres_password: str = os.getenv('postgres_password')
    postgres_user: str = os.getenv('postgres_user')


settings = Settings()


async def connect_create_if_not_exists(user, database, password, host):
    """Do a 20 attempts to connect and create database"""
    for i in range(20):
        try:
            conn = await asyncpg.connect(
                user=user, database=database,
                password=password, host=host
            )
            await conn.close()
            break
        except asyncpg.InvalidCatalogNameError:
            # Database does not exist, create it.
            sys_conn = await asyncpg.connect(
                database='template1',
                user='postgres',
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
    """Run database creation in DMS"""
    asyncio.run(
        connect_create_if_not_exists(
            settings.postgres_user,
            settings.postgres_db,
            settings.postgres_password,
            settings.postgres_host
        )
    )
    logger.info(f'DB initialization with name {settings.postgres_db} is done')


if __name__ == '__main__':
    run_init_db()
