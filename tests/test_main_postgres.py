from asyncio import TaskGroup

from tests.service import User
from tests.service import UserCreateSchema
from tests.service import UserService
from tests.service import UserUpdateSchema


async def test_get_void_list():
    async with UserService() as service:
        users = await service.get_list()
    assert len(users.all()) == 0


test_user_id = 0


async def test_create():
    async with UserService() as service:
        user: User = await service.create(UserCreateSchema(name="test"))
    assert isinstance(user.id, int)
    assert isinstance(user.name, str)
    assert user.name == "test"
    global test_user_id
    test_user_id = user.id


async def test_get_list_with_one():
    async with UserService() as service:
        users = await service.get_list()
    assert len(users.all()) == 1


async def get_user_by_id():
    assert test_user_id != 0
    async with UserService() as service:
        user = await service.get(test_user_id)
    assert user.name == "test"
    assert user.id == test_user_id


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


async def test_get_list_with_pagination():
    async with UserService() as service:
        users = await service.list(page=2, count=3)
    assert len(users.all()) == 3


async def test_update():
    async with UserService() as service:
        await service.update(
            test_user_id,
            UserUpdateSchema(name="test_updated")
        )
        user = await service.get(test_user_id)
    assert user.id == test_user_id
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
    global test_user_id
    async with UserService() as service:
        await service.delete(test_user_id)
        user = await service.get(test_user_id)
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
