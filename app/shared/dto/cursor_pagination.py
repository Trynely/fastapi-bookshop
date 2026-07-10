from dataclasses import dataclass
from typing import TypeVar, List, Union

T = TypeVar("T")

@dataclass(frozen=True, slots=True)
class CursorPaginationDTO:
    items: List[T]
    next_cursor: Union[int, str, None]
    has_more: bool