import os
from abc import abstractmethod

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError


class DBConfigureInterface:
    @abstractmethod
    def get_url(self) -> str:
        ...

    @abstractmethod
    def get_url_with_default_db_name(self) -> str:
        ...

    @abstractmethod
    def get_db_type(self) -> str:
        ...

    @abstractmethod
    def get_db_name(self) -> str:
        ...

    @abstractmethod
    def get_db_user(self) -> str:
        ...


class DBHostNotSetError(Exception):
    def __init__(self):
        super().__init__("DB host variable was not found in .env file and environment variables")


class DBNameNotSetError(Exception):
    def __init__(self):
        super().__init__("DB name variable was not found in .env file and environment variables")


class DBConfigurationNotFoundError(Exception):
    def __init__(self):
        super().__init__("Valid DB configuration was not found")


class OldPostgresSQLDBConfiguration(DBConfigureInterface, BaseSettings):
    postgres_env_warning: bool = True
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    pg_default_envs_link = "https://www.postgresql.org/docs/current/libpq-envars.html"

    postgres_host: str = os.getenv('POSTGRES_HOST', '')
    postgres_database: str = os.getenv('POSTGRES_DATABASE', '')
    postgres_port: str = os.getenv('POSTGRES_PORT', "5432")
    postgres_password: str = os.getenv('POSTGRES_PASSWORD', "postgres")
    postgres_user: str = os.getenv('POSTGRES_USER', "postgres")

    def get_url(self) -> str:
        logger.warning(
            "POSTGRES_<setting> is deprecated. "
            "Please, use PG<setting>\n"
            "See {pg_default_envs_link}"
        )
        if not self.pghost:
            raise DBHostNotSetError()
        if not self.pgdatabse:
            raise DBNameNotSetError()
        return f'postgres+asyncpg://' \
               f'{self.postgres_user}:{self.postgres_password}' \
               f'@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}'

    def __str__(self):
        return self.get_url()

    def get_db_type(self) -> str:
        return 'postgres'

    def get_db_name(self) -> str:
        return self.postgres_database

    def get_db_user(self) -> str:
        return self.postgres_user

    def _validate(self):
        if self.postgres_env_warning:
            logger.warning(
                "POSTGRES_<setting> is deprecated. "
                "Please, use PG<setting>\n"
                "See {pg_default_envs_link}\n"
                "Set POSTGRES_ENV_WARNING=false to ignore it"
            )
            self.postgres_env_warning = False

        if not self.postgres_host:
            raise DBHostNotSetError()
        if not self.postgres_database:
            raise DBNameNotSetError()

    def get_url_with_default_db_name(self) -> str:
        return f'postgres+asyncpg://' \
               f'{self.postgres_user}:{self.postgres_password}' \
               f'@{self.postgres_host}:{self.postgres_port}/template1'


class PostgresSQLDBConfiguration(DBConfigureInterface, BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    name = 'postgres'

    pghost: str = os.getenv('PGHOST', '')
    pgdatabase: str = os.getenv('PGDATABASE', '')
    pgport: str = os.getenv('PGPORT', "5432")
    pgpassword: str = os.getenv('PGPASSWORD', "postgres")
    pguser: str = os.getenv('PGUSER', "postgres")

    def get_url(self) -> str:
        if not self.pghost:
            raise DBHostNotSetError()
        if not self.pgdatabase:
            raise DBNameNotSetError()
        return f'postgres+asyncpg://' \
               f'{self.pguser}:{self.pgpassword}' \
               f'@{self.pghost}:{self.pgport}/{self.pgdatabase}'

    def __str__(self):
        return self.get_url()

    def get_db_type(self) -> str:
        return 'postgres'

    def get_db_name(self) -> str:
        return self.pgdatabase

    def get_db_user(self) -> str:
        return self.pguser

    def _validate(self):
        if not self.pghost:
            raise DBHostNotSetError()
        if not self.pgdatabse:
            raise DBNameNotSetError()

    def get_url_with_default_db_name(self) -> str:
        return f'postgres+asyncpg://' \
               f'{self.pguser}:{self.pgpassword}' \
               f'@{self.pghost}:{self.pgport}/template1'

class MySQLDBConfiguration(DBConfigureInterface, BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    mysql_host: str = os.getenv('MYSQL_HOST')
    mysql_db: str = os.getenv('MYSQL_DB')
    mysql_port: str = os.getenv('MYSQL_PORT', "3306")
    mysql_password: str = os.getenv('MYSQL_PASSWORD', "")
    mysql_user: str = os.getenv('MYSQL_USER', "root")

    def get_url(self) -> str:
        if not self.mysql_host:
            raise DBHostNotSetError()
        if not self.mysql_db:
            raise DBNameNotSetError()
        return f'mysql+mysqlconnector://' \
               f'{self.mysql_user}:{self.mysql_password}' \
               f'@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}'

    def __str__(self):
        return self.get_url()

    def get_db_type(self) -> str:
        return 'mysql'

    def get_db_name(self) -> str:
        return self.mysql_db

    def get_db_user(self) -> str:
        return self.mysql_user

    def get_url_with_default_db_name(self) -> str:
        return f'mysql+aiomysql://' \
               f'{self.mysql_user}:{self.mysql_password}' \
               f'@{self.mysql_host}:{self.mysqlport}'

class DBConfigurator:
    configuration_classes = [PostgresSQLDBConfiguration, MySQLDBConfiguration]

    def __init__(self):
        self.configuration: DBConfigureInterface = DBConfigureInterface()
        self._try_configures()

    def _try_configures(self):
        for configuration_class in self.configuration_classes:
            try:
                configuration = configuration_class()
                self.configure_url = configuration.get_url()
                return
            except (DBHostNotSetError, DBNameNotSetError, SettingsError):
                pass
        raise DBConfigurationNotFoundError
