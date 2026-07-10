from typing import Union
from pydantic import BaseModel

class CursorPaginationRESP(BaseModel):
    next: Union[int, str, None]
    has_next: bool