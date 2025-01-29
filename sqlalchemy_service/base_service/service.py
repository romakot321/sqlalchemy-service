import uuid
from typing import Any
from typing import Callable
from typing import Generic
from typing import Self
from typing import TypedDict
from typing import TypeVar

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import exc
from sqlalchemy import ScalarResult
from sqlalchemy import select
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute as TableAttr

from sqlalchemy_service.base_db.base import Base as BaseTable
from sqlalchemy_service.base_db.base import get_session

F = TypeVar('F', bound=Callable[..., Any])


class CopySignature(Generic[F]):
    def __init__(self, target: F) -> None: ...

    def __call__(self, wrapped: Callable[..., Any]) -> F: ...


class TableAttributeWithSubqueryLoad(TypedDict):
    parent: TableAttr
    children: list[TableAttr]


type TableAttributesType = TableAttr | TableAttributeWithSubqueryLoad | list[
    TableAttr | TableAttributeWithSubqueryLoad
    ]


class QueryService[Table: BaseTable]:
    base_table: type[Table]

    def __init__(self):
        pass

    @classmethod
    def _get_list_query(
            cls,
            page: int | None = None,
            count: int | None = None,
            select_in_load: TableAttributesType | None = None,
            none_as_value: bool = False,
            **filters
    ) -> Select:
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
        query = select(cls.base_table)
        return cls._query_add_select_in_load(query, select_in_load)

    @classmethod
    def _query_filter[SelectType: Select](
            cls,
            query: SelectType,
            none_as_values: bool = False,
            **filters
    ) -> SelectType:
        if none_as_values:
            return query.filter_by(**filters)
        return cls.__query_filter_without_none_as_value(query, **filters)

    @classmethod
    def _filter_query(cls, none_as_values: bool = False, **filters) -> Select:
        query = select(cls.base_table)
        return cls._query_filter(
            query,
            none_as_values=none_as_values,
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
        query = select(cls.base_table)
        return cls._query_like_filter(query, **kwargs)

    @classmethod
    def _query_like_filter(cls, query, **kwargs):
        for key, value in kwargs.items():
            if value is None:
                continue
            filter_ = '%{}%'.format(value)
            query = query.filter(getattr(cls.base_table, key).like(filter_))
        return query


try:
    from fastapi import Depends
except ImportError:
    from sqlalchemy_service.base_service._fastapi_mock import Depends

try:
    from fastapi.params import Depends as DependsClass
except ImportError:
    DependsClass = None

try:
    from fastapi import HTTPException
except ImportError:
    from sqlalchemy_service.base_service._fastapi_mock import HTTPException

try:
    from fastapi import Response
except ImportError:
    from sqlalchemy_service.base_service._fastapi_mock import Response


class BaseService[Table: BaseTable, IDType](QueryService):
    base_table: type[Table]

    def __init__(
            self,
            session: AsyncSession = Depends(get_session),
            response: Response = Response
    ):
        super().__init__()
        self.response = response
        self._session_creator = None
        self.session = session
        self._need_commit_and_close = False
        if not isinstance(session, DependsClass):
            self._need_commit_and_close = True

    async def _get_list(
            self,
            *args, **kwargs
    ) -> ScalarResult[Table]:
        query = self._get_list_query(
            *args, **kwargs
        )
        return await self.session.scalars(query)

    async def _get_one(
            self,
            select_in_load: TableAttributesType | None = None,
            mute_not_found_exception: bool = False,
            **filters
    ) -> Table:
        query = self._filter_query(**filters)
        if select_in_load is not None:
            query = self._query_add_select_in_load(query, select_in_load)
        obj = await self.session.scalar(query)

        if obj is None and not mute_not_found_exception:
            raise HTTPException(status_code=404)

        return obj

    async def _commit(self):
        if self._need_commit_and_close:
            try:
                await self.session.commit()
            except exc.IntegrityError as e:
                await self.session.rollback()
                logger.exception(e)
                if 'is not present in table' in str(e.orig):
                    table_name = str(e.orig).split('is not present in table')[
                        1].strip().capitalize()
                    table_name = table_name.strip('"').strip("'")
                    raise HTTPException(
                        status_code=404,
                        detail=f'{table_name} not found'
                    )
                raise HTTPException(status_code=409)

    async def _update(
            self,
            object_filter: dict[str, Any] | IDType,
            object_schema: BaseModel | dict | None = None,
            none_as_value: bool = False,
            re_get: bool = False,
            **kwargs
    ) -> Table:
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
        if re_get:
            if isinstance(object_filter, dict):
                obj = await self._get_one(**object_filter)
            else:
                obj = await self._get_one(id=object_filter)
        await self.session.refresh(obj)
        return obj

    async def _update_obj(
            self,
            obj: Table,
            object_schema: BaseModel | dict | None = None,
            none_as_value: bool = False,
            **kwargs
    ) -> Table:
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
        await self.session.refresh(obj)
        self.response.status_code = 201
        return obj

    async def _delete(self, object_filter: dict[str, Any] | IDType):
        if isinstance(object_filter, dict):
            obj = await self._get_one(**object_filter)
        else:
            obj = await self._get_one(id=object_filter)
        await self._delete_obj(obj)

    async def _delete_obj(self, obj: Table):
        await self.session.delete(obj)
        await self._commit()
        self.response.status_code = 204

    async def __aenter__(self) -> Self:
        if not isinstance(self.session, AsyncSession):
            self._session_creator = get_session()
            self.session = await anext(self._session_creator)
            logger.debug(f'Create session ({self.session}) with aenter')
            self._need_commit_and_close = True
        return self

    async def __aexit__(self, *exc_info):
        if self._need_commit_and_close:
            try:
                self.session = await anext(self._session_creator)
                logger.debug(f'Stop session ({self.session}) with aexit')
            except StopAsyncIteration:
                pass
