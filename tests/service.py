from pydantic import BaseModel
from sqlalchemy import ScalarResult
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as column

from sqlalchemy_service import Base
from sqlalchemy_service import BaseService
from sqlalchemy_service.base_db.base import ServiceEngine


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = column(primary_key=True, autoincrement=True)
    name: Mapped[str]


class UserCreateSchema(BaseModel):
    name: str


class UserUpdateSchema(BaseModel):
    name: str | None = None


# You can manually set urls for engines, or use autodetect
engine = ServiceEngine()


class UserService[Table: User, int](BaseService):
    base_table = User
    engine = engine

    async def create(self, schema: UserCreateSchema) -> User:
        return await self._create(schema)

    async def list(self, page=None, count=None) -> ScalarResult[User]:
        return await self._get_list(page=page, count=count)

    async def get(self, user_id: int) -> User:
        """Return user. If user not found, return None"""
        return await self._get_one(id=user_id, mute_not_found_exception=True)

    async def get_list(self) -> ScalarResult[User]:
        return await self._get_list()

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
