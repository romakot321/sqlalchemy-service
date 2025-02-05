import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class DBConfigureInterface:
    def __str__(self):
        ...

    def get_url(self) -> str:
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


class PostgresSQLDBConfiguration(DBConfigureInterface, BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    pghost: str = os.getenv('PGHOST')
    pgdb: str = os.getenv('PGDB')
    pgport: str = os.getenv('PGPORT') or "5432"
    pgpassword: str = os.getenv('PGPASSWORD') or "postgres"
    pguser: str = os.getenv('PGUSER') or "postgres"

    def get_url(self) -> str:
        if not self.pghost:
            raise DBHostNotSetError()
        if not self.pgdb:
            raise DBNameNotSetError()
        return f'{self.database_type}+{self.database_driver}://' \
               f'{self.database_user}:{self.database_password}' \
               f'@{self.database_host}/{self.database_db}'

    def __str__(self):
        return self.get_url()


class MySQLDBConfiguration(DBConfigureInterface, BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra="allow")

    mysql_host: str = os.getenv('MYSQL_HOST')
    mysql_db: str = os.getenv('MYSQL_DB')
    mysql_port: str = os.getenv('MYSQL_PORT') or "3306"
    mysql_password: str = os.getenv('MYSQL_PASSWORD') or ""
    mysql_user: str = os.getenv('MYSQL_USER') or "root"

    def get_url(self) -> str:
        if not self.mysql_host:
            raise DBHostNotSetError()
        if not self.mysql_db:
            raise DBNameNotSetError()
        return f'{self.database_type}+{self.database_driver}://' \
               f'{self.database_user}:{self.database_password}' \
               f'@{self.database_host}/{self.database_db}'

    def __str__(self):
        return self.get_url()


class DBConfigurator:
    configures = [PostgresSQLDBConfiguration, MySQLDBConfiguration]

    def __init__(self):
        self.configure_url = ''
        self._try_configures()

    def get_url(self) -> str:
        return self.configure_url

    def __str__(self):
        return self.get_url()

    def _try_configures(self):
        for configure in self.configures:
            try:
                self.configure_url = configure().get_url()
                return
            except (DBHostNotSetError, DBNameNotSetError):
                pass
        raise DBConfigurationNotFoundError
