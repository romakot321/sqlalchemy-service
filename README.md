from sqlalchemy_service.base_db.db_configure import MySQLDBConfigurationfrom sqlalchemy.ext.asyncio import AsyncSessionfrom typing import AsyncGenerator

# Sqlalchemy-service
This is a library that simplifies working with database CRUD queries and connection management.

## Features
- A class to reduce the amount of code needed for database CRUD queries and connection management.

## Installation
- `pip install sqlalchemy-service[postresql]`
- `pip install sqlalchemy-service[mysql]`
- `pip install sqlalchemy-service[postgresql,fastapi]` for fastapi support(http exceptions and dependency injection)

## Usage
- Need environment set: POSTGRES_HOST, POSTGRES_DATABASE, POSTGRES_PASSWORD, POSTGRES_USER

```python3
import asyncio
from random import randint

from pydantic import BaseModel
from sqlalchemy import ScalarResult
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as column

from sqlalchemy_service import Base
from sqlalchemy_service import BaseService
from sqlalchemy_service.base_db.base import ServiceEngine
from sqlalchemy_service.base_db.db_configure import MySQLDBConfiguration


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = column(primary_key=True)
    name: Mapped[str]


class UserCreateSchema(BaseModel):
    name: str


class UserUpdateSchema(BaseModel):
    name: str | None = None


# You can manually set urls for engines, or use autodetect
engine_1 = ServiceEngine()
engine_2 = ServiceEngine(MySQLDBConfiguration().get_url())


class UserService[Table: User, int](BaseService):
    base_table = User
    engine = engine_1

    # Redefine BaseService.get_session to connect with 2 engines
    # Just don't rewrite it to connect with one engine
    async def get_session(self):
        if randint(0, 1):
            return engine_1
        return engine_2

    async def create(self, schema: UserCreateSchema) -> User:
        return await self._create(schema)

    async def list(self, page=None, count=None) -> ScalarResult[User]:
        return await self._get_list(page=page, count=count)

    async def get(self, user_id: int) -> User:
        """Return user. If user not found, throws 404 HTTPException"""
        return await self._get_one(id=user_id)

    async def update(self, user_id: int, schema: UserUpdateSchema) -> User:
        return await self._update(user_id, schema)

    async def delete(self, user_id: int):
        await self._delete(user_id)

    async def count(self) -> int:
        return await self._count()

    async def count_with_name_like(self, name: str) -> int:
        query = self._count_query()
        query = self._query_like_filter(query, name=name)
        return await self.session.scalar(query)


async def main():
    # Use alembic to create database schema
    async with UserService() as service:
        print(await service.create(UserCreateSchema(name="test")))


asyncio.run(main())
```

# Updates
### 1.0.0:
- custom engine style
- more use-ready commands