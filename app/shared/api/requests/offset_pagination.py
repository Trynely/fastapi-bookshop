from pydantic import BaseModel, Field
from app.core.config.base import get_settings

settings = get_settings()


class OffsetPagination(BaseModel):
    """Offset-пагинация: /reviews/{slug}?page=2&page_size=20."""

    page: int = Field(
        default=1,
        ge=1,
        description="Номер страницы (начиная с 1)",
    )
    page_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Размер страницы (по умолчанию — из настроек)",
    )

    @property
    def limit(self) -> int:
        return self.page_size or settings.db.limit

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit
