"""Module with base classes for db connection and queries management"""

import uuid
from typing import Any
from typing import AsyncGenerator
from typing import Self
from typing import TypedDict

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import ScalarResult
from sqlalchemy import Select
from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute as TableAttr

from sqlalchemy_service.base_db.base import Base as BaseTable
from sqlalchemy_service.base_db.base import ServiceEngine


class TableAttributeWithSubqueryLoad(TypedDict):
    parent: TableAttr
    children: list[TableAttr]


type TableAttributesType = TableAttr | TableAttributeWithSubqueryLoad | list[
    TableAttr | TableAttributeWithSubqueryLoad
    ]


class QueryService[Table: BaseTable]:
    """Service with query builders"""
    base_table: type[Table]

    def __init__(self):
        pass

    def _count_query(self, none_as_value: bool = False, **filters) -> Select:
        query = select(func.count()).select_from(self.base_table)
        return self._query_filter(
            query,
            none_as_value=none_as_value,
            **filters
        )


    @classmethod
    def _get_list_query(
            cls,
            page: int | None = None,
            count: int | None = None,
            select_in_load: TableAttributesType | None = None,
            none_as_value: bool = False,
            **filters
    ) -> Select:
        """
        Query builder for select list of models.
        Implement a filters and pagination
        """
        query = select(cls.base_table)
        if select_in_load is not None:
            query = cls._query_add_select_in_load(query, select_in_load)
        cls.__query_pagination(query, page, count)
        query = cls._query_filter(query, none_as_value, **filters)
        return query

    @staticmethod
    def __query_pagination(
            query: Select,
            page: int | None = None,
            count: int | None = None
    ):
        if page is None and count is not None:
            page = 0
        if page is not None and count is None:
            count = 20
        if page is not None and count is not None:
            offset = page * count
            query = query.offset(offset).limit(count)
        return query

    @staticmethod
    def _query_add_select_in_load(
            query: Select,
            table_attributes: TableAttributesType
    ) -> Select:
        """Builder for selectinload for model(aka relationship)"""
        if not isinstance(table_attributes, list):
            table_attributes = [table_attributes]
        select_in_loads = []
        for table_attr in table_attributes:
            if isinstance(table_attr, dict):
                select_in_load = selectinload(table_attr['parent'])
                for table_attr_child in table_attr['children']:
                    select_in_load.subqueryload(table_attr_child)
                select_in_loads.append(select_in_load)
            else:
                select_in_loads.append(selectinload(table_attr))
        query = query.options(
            *select_in_loads
        )
        return query

    @classmethod
    def _select_in_load_query(
            cls,
            select_in_load: TableAttributesType
    ) -> Select:
        """Build a selectinload query for specified relationships"""
        query = select(cls.base_table)
        return cls._query_add_select_in_load(query, select_in_load)

    @classmethod
    def _query_filter[SelectType: Select](
            cls,
            query: SelectType,
            none_as_value: bool = False,
            **filters
    ) -> SelectType:
        """Append the query with filters"""
        if none_as_value:
            return query.filter_by(**filters)
        return cls.__query_filter_without_none_as_value(query, **filters)

    @classmethod
    def _filter_query(cls, none_as_value: bool = False, **filters) -> Select:
        """Build a query with filters"""
        query = select(cls.base_table)
        return cls._query_filter(
            query,
            none_as_value=none_as_value,
            **filters
        )

    @staticmethod
    def __query_filter_without_none_as_value(query, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                query = query.filter_by(**{key: value})
        return query

    @classmethod
    def _like_filter_query(cls, **kwargs) -> Select:
        """Build a query with like filters"""
        query = select(cls.base_table)
        return cls._query_like_filter(query, **kwargs)

    @classmethod
    def _query_like_filter(cls, query, **kwargs):
        """Append a query with like filters"""
        for key, value in kwargs.items():
            if value is None:
                continue
            filter_ = '%{}%'.format(value)
            query = query.filter(getattr(cls.base_table, key).like(filter_))
        return query


try:
    from fastapi import Depends
    from fastapi.params import Depends as DependsClass
    from fastapi import HTTPException
    from fastapi import Response
except ImportError:
    logger.info("Use configuration with mock fastapi")
    from sqlalchemy_service.base_service._fastapi_mock import Depends


    DependsClass = Depends
    from sqlalchemy_service.base_service._fastapi_mock import HTTPException
    from sqlalchemy_service.base_service._fastapi_mock import Response


class BaseService[Table: BaseTable, IDType](QueryService):
    """
    Base class for service with database connection.
    Implement base queries builders, session management
    and base db exceptions handlers.
    """
    base_table: type[Table]
    engine: ServiceEngine

    def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Method creates all sessions that is used in the BaseService.
        You can redefine it for more a flexable behavior.
        """
        return self.engine.get_session()

    def __init__(
            self,
            session: AsyncSession = Depends(get_session),
            response: Response = Response,
    ):
        super().__init__()
        self.response = response
        self._session_creator = None
        self.session = session
        self.objects_to_refresh = []
        # isinstance(session, DependsClass) == True means that
        # FastAPI "Depends" was not called.
        # Then you need use python with-syntax to create and close session
        logger.debug(f'Initialize Service with {type(session)=}')
        self._need_commit_and_close: bool = isinstance(session, DependsClass)
        logger.debug(f'Initialize Service with {self._need_commit_and_close=}')

    async def _count(self, none_as_value: bool = False, **filters) -> int:
        query = self._count_query(none_as_value=none_as_value, **filters)
        return await self.session.scalar(query)

    async def _get_list(
            self,
            page: int | None = None,
            count: int | None = None,
            select_in_load: TableAttributesType | None = None,
            none_as_value: bool = False,
            **filters
    ) -> ScalarResult[Table]:
        """
        Get models list by filters. Defaults page to 0 and count to 20

        """
        query = self._get_list_query(
            page=page,
            count=count,
            select_in_load=select_in_load,
            none_as_value=none_as_value,
            **filters
        )
        return await self.session.scalars(query)

    async def _get_one(
            self,
            select_in_load: TableAttributesType | None = None,
            mute_not_found_exception: bool = False,
            **filters
    ) -> Table:
        """Get model filters.
        If model not found and mute_not_found_exception is False,
        then throw HTTPException with 404 status (Not found)
        """
        query = self._filter_query(**filters)
        if select_in_load is not None:
            query = self._query_add_select_in_load(query, select_in_load)
        obj = await self.session.scalar(query)

        if obj is None and not mute_not_found_exception:
            raise HTTPException(status_code=404)

        return obj


    async def _update(
            self,
            object_filter: dict[str, Any] | IDType,
            object_schema: BaseModel | dict | None = None,
            none_as_value: bool = False,
            **kwargs
    ) -> Table:
        """
        Get model by filters and update its rows with schema and kwargs.
        if none_as_value is None, then skip keys in schema, which value is none.
        Update model, and if no fields is updated,
        then set fastapi response status_code to 304(Not modified).
        Return updated model with new fields.
        """
        if isinstance(object_filter, dict):
            obj = await self._get_one(**object_filter)
        else:
            obj = await self._get_one(id=object_filter)
        obj = await self._update_obj(
            obj,
            object_schema,
            none_as_value,
            **kwargs
        )
        self.objects_to_refresh.append(obj)
        return obj

    async def _update_obj(
            self,
            obj: Table,
            object_schema: BaseModel | dict | None = None,
            none_as_value: bool = False,
            **kwargs
    ) -> Table:
        """
        Update model rows with schema and kwargs.
        if none_as_value is None, then skip keys in schema, which value is none.
        Update model, and if no fields is updated,
        then set fastapi response status_code to 304(Not modified).
        """
        if object_schema is None:
            object_schema = {}
        elif isinstance(object_schema, BaseModel):
            object_schema = object_schema.model_dump()

        modified = False
        for key, value in (object_schema | kwargs).items():
            attr = getattr(obj, key)
            if not none_as_value and value is None:
                continue
            field_is_modified = attr != value
            setattr(obj, key, value)

            modified = modified or field_is_modified
        self.session.add(obj)
        await self._commit()
        if not modified:
            self.response.status_code = 304
        return obj

    async def _create(
            self,
            object_schema: BaseModel | None = None,
            creator_id: uuid.UUID | None = None,
            **kwargs
    ) -> Table:
        """
        Create model from schema and kwargs,
        set fastapi response status_code to 201(Created)
        and return created model
        """
        obj_dict = {}
        if object_schema is not None:
            obj_dict = object_schema.model_dump()

        if creator_id is not None:
            kwargs['creator_id'] = creator_id
            kwargs['editor_id'] = creator_id

        obj = self.base_table(
            **obj_dict, **kwargs
        )

        self.session.add(obj)
        await self._commit()
        self.objects_to_refresh.append(obj)
        self.response.status_code = 201
        return obj


    async def _delete(self, object_filter: dict[str, Any] | IDType):
        """Get model by filters and delete it"""
        if isinstance(object_filter, dict):
            obj = await self._get_one(**object_filter)
        else:
            obj = await self._get_one(id=object_filter)
        await self._delete_obj(obj)

    async def _delete_obj(self, obj: Table):
        """
        Delete model and set fastapi response status_code to 204(No content)
        """
        await self.session.delete(obj)
        await self._commit()
        self.response.status_code = 204

    async def refresh(self):
        if self.objects_to_refresh and self._need_commit_and_close:
            logger.debug(
                f'Commit and yry to refresh objects, '
                f'count={len(self.objects_to_refresh)}'
            )
            await self.session.flush(self.objects_to_refresh)
        for _ in range(len(self.objects_to_refresh)):
            await self.session.refresh(self.objects_to_refresh.pop())

    async def _commit(self):
        """
        Commit changes.
        Handle sqlalchemy.exc.IntegrityError.
        If exception is not found error,
        then throw HTTPException with 404 status (Not found).
        Else log exception and throw HTTPException with 409 status (Conflict)
        """
        if not self._need_commit_and_close:
            logger.debug('Service no commit')
            return
        try:
            logger.debug('Service try commit')
            await self.session.commit()
            logger.debug('Service commit successful')
        except exc.IntegrityError as e:
            logger.warning('Service rollback')
            await self.session.rollback()
            if 'is not present in table' not in str(e.orig):
                logger.exception(e)
                raise HTTPException(status_code=409)
            table_name = str(e.orig).split('is not present in table')[1]
            table_name = table_name.strip().capitalize()
            table_name = table_name.strip('"').strip("'")
            raise HTTPException(
                status_code=404,
                detail=f'{table_name} not found'
            )

    async def __aenter__(self) -> Self:
        if not isinstance(self.session, AsyncSession):
            self._session_creator = self.get_session()
            self.session = await anext(self._session_creator)
            logger.debug(f'Create session ({self.session}) with aenter')
        self._need_commit_and_close = False
        return self

    async def __aexit__(self, *exc_info):
        self._need_commit_and_close = True
        await self._commit()
        self._need_commit_and_close = False
        await self.refresh()
        try:
            self.session = await anext(self._session_creator)
        except StopAsyncIteration:
            logger.debug(f'Stop session ({self.session}) with aexit')
