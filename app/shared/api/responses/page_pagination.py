from pydantic import BaseModel

class PagePaginationRESP(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int