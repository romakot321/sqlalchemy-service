import typing
from typing import Annotated, Any

from typing_extensions import Doc


class HTTPException:
    def __new__(
            cls,
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
        raise ValueError(f'Error with HTTP status code: {status_code}, details: {detail}')


def Depends(*args, **kwargs):
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

    def render(self, content: typing.Any) -> bytes | memoryview:
        if content is None:
            return b""
        if isinstance(content, (bytes, memoryview)):
            return content
        return content.encode(self.charset)  # type: ignore

    def init_headers(self, headers: typing.Mapping[str, str] | None = None) -> None:
        if headers is None:
            raw_headers: list[tuple[bytes, bytes]] = []
            populate_content_length = True
            populate_content_type = True
        else:
            raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
            keys = [h[0] for h in raw_headers]
            populate_content_length = b"content-length" not in keys
            populate_content_type = b"content-type" not in keys

        body = getattr(self, "body", None)
        if (
                body is not None
                and populate_content_length
                and not (self.status_code < 200 or self.status_code in (204, 304))
        ):
            content_length = str(len(body))
            raw_headers.append((b"content-length", content_length.encode("latin-1")))

        content_type = self.media_type
        if content_type is not None and populate_content_type:
            if content_type.startswith("text/") and "charset=" not in content_type.lower():
                content_type += "; charset=" + self.charset
            raw_headers.append((b"content-type", content_type.encode("latin-1")))

        self.raw_headers = raw_headers

    def set_cookie(self, *args, **kwargs) -> None:
        pass

    def delete_cookie(self, *args, **kwargs) -> None:
        pass

    async def __call__(self, *args, **kwargs) -> None:
        pass
