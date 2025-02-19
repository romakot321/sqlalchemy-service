"""Module with mocks for fastapi classes, which used in this library"""

import typing
from typing import Annotated
from typing import Any

from typing_extensions import Doc


class HTTPException(Exception):
    def __init__(
            self,
            status_code: Annotated[
                int,
                Doc(
                    """
                    HTTP status code to send to the client.
                    """
                ),
            ],
            detail: Annotated[
                Any,
                Doc(
                    """
                    Any data to be sent to the client in the `detail` key of the JSON
                    response.
                    """
                ),
            ] = None,
            headers: Annotated[
                dict[str, str] | None,
                Doc(
                    """
                    Any headers to send to the client in the response.
                    """
                ),
            ] = None,
    ) -> None:
        super().__init__(
            f'Error with HTTP status code: {status_code}, details: {detail}'
        )


class Depends:
    def __init__(self, *args, **kwargs):
        pass


class Response:
    media_type = None
    charset = "utf-8"

    def __init__(self, *args, **kwargs) -> None:
        self.status_code = None
        self.media_type = None
        self.background = None
        self.body = None
        self.headers = {}

    def render(self, content: typing.Any) -> None:
        ...

    def init_headers(
            self,
            headers: typing.Mapping[str, str] | None = None
    ) -> None:
        ...

    def set_cookie(self, *args, **kwargs) -> None:
        ...

    def delete_cookie(self, *args, **kwargs) -> None:
        ...

    async def __call__(self, *args, **kwargs) -> None:
        ...
