from dataclasses import dataclass
from typing import List, TypeVar

T = TypeVar("T")

@dataclass(frozen=True, slots=True)
class PagePaginationResult:
    items: List[T]
    page: int
    page_size: int
    total: int
    pages: int