from pydantic import BaseModel, Field


class CursorIDPaginationREQT(BaseModel):
    """Cursor-пагинация по id: ?id_cursor=<последний полученный id>."""

    id_cursor: int | None = Field(
        default=None,
        ge=1,
        description="ID последнего элемента предыдущей страницы",
    )


class CursorIDRandomPagination(CursorIDPaginationREQT):
    seed: str


class CursorEncodedPaginationREQT(BaseModel):
    """Cursor-пагинация по непрозрачному курсору: ?encoded_cursor=<next из прошлого ответа>."""

    encoded_cursor: str | None = Field(
        default=None,
        max_length=512,
        description="Значение `next` из предыдущего ответа",
    )


class CursorMD5PaginationREQT(BaseModel):
    md5_cursor: str | None = Field(
        default=None,
        min_length=32,
        max_length=32,
        description="MD5-курсор — значение `next` из предыдущего ответа",
    )


class CursorMD5RandomPaginationREQT(CursorMD5PaginationREQT):
    seed: str = Field(description="Seed для стабильного случайного порядка")
