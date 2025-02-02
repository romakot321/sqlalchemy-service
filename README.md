# Sqlalchemy-service
This is a library that simplifies working with database CRUD queries and connection management.

## Features
- A class to reduce the amount of code needed for database CRUD queries and connection management.

## Installation
- `pip install sqlalchemy-service`
- `pip install sqlalchemy-service[fastapi]` for fastapi support(http exceptions and dependency injection)

## Usage
- Need environment set: POSTGRES_HOST, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER
```python3
from sqlalchemy_service import BaseService, Base, init_models
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as column
from pydantic import BaseModel
import asyncio


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = column(primary_key=True)
    name: Mapped[str]


class UserCreateSchema(BaseModel):
    name: str


class UserUpdateSchema(BaseModel):
    name: str | None = None


class UserService[Table: User, int](BaseService):
    base_table = User

    async def create(self, schema: UserCreateSchema) -> User:
        return await self._create(schema)

    async def list(self, page=None, count=None) -> list[User]:
        return await self._get_list(page=page, count=count)

    async def get(self, user_id: int) -> User:
        """Return user. If user not found, throws 404 HTTPException"""
        return await self._get_one(id=user_id)

    async def update(self, user_id: int, schema: UserUpdateSchema) -> User:
        return await self._update(user_id, schema)

    async def delete(self, user_id: int):
        await self._delete(user_id)


async def main():
    await init_models()
    async with UserService() as service:
        print(await service.create(UserCreateSchema(name="test")))


asyncio.run(main())
```
