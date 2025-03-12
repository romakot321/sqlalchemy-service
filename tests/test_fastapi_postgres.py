from fastapi import Depends
from httpx import AsyncClient
from loguru import logger
from sqlalchemy import create_engine

from sqlalchemy_service import Base
from sqlalchemy_service.base_db.create import run_init_db
from sqlalchemy_service.base_db.db_configure import DBConfigurator
from tests.fastapi_app import app
from tests.service import UserCreateSchema
from tests.service import UserService


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


@app.post('/users')
async def create(
        user_schema: UserCreateSchema,
        user_service: UserService = Depends(UserService.depend),
):
    user = await user_service.create(user_schema)
    logger.debug(f'{user.id=}')
    await user_service.refresh()
    return user


@app.get('/users/{user_id}')
async def get(
        user_id: int,
        user_service: UserService = Depends(UserService.depend),
):
    user = await user_service.get(user_id)
    return user



@app.delete('/users/{user_id}')
async def delete(
        user_id: int,
        user_service: UserService = Depends(UserService.depend)
):
    await user_service.delete(user_id)

test_user_id = None

async def test_fastapi_create_user(client: AsyncClient):
    schema = UserCreateSchema(name=f"Ivan")
    response = await client.post('/users', json=schema.model_dump())
    logger.debug(response.content)
    assert response.status_code == 201
    global test_user_id
    user = response.json()
    logger.debug(f'{user=}')
    assert isinstance(user['id'], int)
    test_user_id = user['id']

async def test_fastapi_get_user(client: AsyncClient):
    global test_user_id
    response = await client.get(f'/users/{test_user_id}')
    logger.debug(response.content)
    assert response.status_code == 200
    user = response.json()
    logger.debug(f'{user=}')
    assert isinstance(user['id'], int)
    assert user['id'] == test_user_id


async def test_fastapi_delete_user(client: AsyncClient):
    response = await client.delete(f'/users/{test_user_id}')
    logger.debug(response.content)
    assert response.status_code == 204

