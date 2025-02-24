from asyncio import TaskGroup

from pydantic import BaseModel
from sqlalchemy import ScalarResult
from sqlalchemy import create_engine
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as column

from sqlalchemy_service import Base
from sqlalchemy_service import BaseService
from sqlalchemy_service.base_db.base import ServiceEngine
from sqlalchemy_service.base_db.create import run_init_db
from sqlalchemy_service.base_db.db_configure import DBConfigurator


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


def test_init_db():
    run_init_db()
    sync_engine = create_engine(
        DBConfigurator().configuration.get_url().replace('asyncpg', 'psycopg2'),
        pool_size=1,
        max_overflow=0,
        pool_reset_on_return=True
    )
    Base.metadata.drop_all(sync_engine.engine)
    Base.metadata.create_all(sync_engine.engine)


async def test_get_void_list():
    async with UserService() as service:
        users = await service.get_list()
    assert len(users.all()) == 0


user_id = None


async def test_create():
    async with UserService() as service:
        user: User = await service.create(UserCreateSchema(name="test"))
    assert isinstance(user.id, int)
    assert isinstance(user.name, str)
    assert user.name == "test"
    global user_id
    user_id = user.id


async def test_get_list_with_one():
    async with UserService() as service:
        users = await service.get_list()
    assert len(users.all()) == 1


async def get_user_by_id():
    assert user_id is not None
    async with UserService() as service:
        user = await service.get(user_id)
    assert user.name == "test"
    assert user.id == user_id


multiple_user_ids: list[int] = []


async def test_create_multiple():
    tasks = []
    async with UserService() as service, TaskGroup() as task_group:
        for i in range(10):
            tasks.append(
                task_group.create_task(
                    service.create(UserCreateSchema(name=f"test {i}"))
                )
            )
    tasks_results = [task.result() for task in tasks]
    for i, user in enumerate(tasks_results):
        assert isinstance(user.id, int)
        assert isinstance(user.name, str)
        assert user.name == f"test {i}"
        global multiple_user_ids
        multiple_user_ids.append(user.id)


async def test_get_list_with_multiple():
    async with UserService() as service:
        users = await service.get_list()
    assert len(users.all()) == 11


async def test_update():
    async with UserService() as service:
        await service.update(user_id, UserUpdateSchema(name="test_updated"))
        user = await service.get(user_id)
    assert user.id == user_id
    assert user.name == "test_updated"


async def test_update_multiple():
    global multiple_user_ids
    tasks = []
    async with UserService() as service, TaskGroup() as task_group:
        for i in range(10):
            tasks.append(
                task_group.create_task(
                    service.update(
                        multiple_user_ids[i],
                        UserUpdateSchema(name=f"test_updated {i}")
                    )
                )
            )
    tasks_results = [task.result() for task in tasks]
    for i, user in enumerate(tasks_results):
        assert isinstance(user.id, int)
        assert isinstance(user.name, str)
        assert user.name == f"test_updated {i}"


async def test_like_filter():
    async with UserService() as service:
        count_1 = await service.count_with_name_like('updated ')
        count_2 = await service.count_with_name_like(' ')
        count_3 = await service.count_with_name_like('1')
    assert count_1 == count_2 == 10
    assert count_3 == 1


async def test_delete():
    global user_id
    async with UserService() as service:
        await service.delete(user_id)
        user = await service.get(user_id)
        count = await service.count()
    assert user is None
    assert count == 10


async def test_delete_multiple():
    global multiple_user_ids
    async with UserService() as service, TaskGroup() as task_group:
        for multiple_user_id in multiple_user_ids:
            task_group.create_task(service.delete(multiple_user_id))
    async with UserService() as service:
        count = await service.count()
    assert count == 0


async def test_with_refresh():
    async with UserService() as service:
        await service.create(UserCreateSchema(name='Test Ivan'))
        await service.refresh()
        count = await service.count()
    assert count == 1
