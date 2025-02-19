"""Module with functions for prepare database for using"""

import asyncio

from loguru import logger

from sqlalchemy_service.base_db.db_configure import DBConfigurator
from sqlalchemy_service.base_db.db_configure import DBConfigureInterface


db_configurator = DBConfigurator()


class DriverNotFoundError(Exception):
    def __init__(self):
        super().__init__('Database driver was not found')


if db_configurator.configuration.get_db_type() == 'postgres':
    try:
        import asyncpg as driver
    except ImportError:
        logger.error(
            'You need to install sqlalchemy-service[postgres] '
            'to use postgres configuration'
        )
elif db_configurator.configuration.get_db_type() == 'mariadb':
    try:
        import aiomysql as driver
    except ImportError:
        logger.error(
            'You need to install sqlalchemy-service[mysql] '
            'to use mysql configuration'
        )
else:
    raise DriverNotFoundError()


async def connect_create_if_not_exists(
        db_configuration: DBConfigureInterface
):
    """Do 20 attempts to connect and create database"""
    for i in range(20):
        try:
            url = db_configuration.get_url()
            url = url.replace('+asyncpg', '')
            url = url.replace('+aiomysql', '')
            conn = await driver.connect(url)
            await conn.close()
            break
        except driver.InvalidCatalogNameError:
            # Database does not exist, create it.
            sys_conn = await driver.connect(
                db_configuration.get_url_with_default_db_name().replace(
                    '+asyncpg',
                    ''
                ),
            )
            await sys_conn.execute(
                f'CREATE DATABASE "{db_configuration.get_db_name()}" '
                f'OWNER "{db_configuration.get_db_user()}"'
            )
            await sys_conn.close()
            break
        except Exception as e:
            logger.exception(
                f"Error on database connection: {str(e)}\n[{i + 1}/20] "
                f"Retry in 5 seconds..."
            )
            await asyncio.sleep(5)


def run_init_db():
    """
        Run database creation in DMS.
        Use provided driver_name for driver import
    """
    asyncio.run(
        connect_create_if_not_exists(
            db_configurator.configuration,
        )
    )
    logger.info(
        f'DB initialization with name '
        f'{db_configurator.configuration.get_db_name()} is done'
    )


if __name__ == '__main__':
    run_init_db()
