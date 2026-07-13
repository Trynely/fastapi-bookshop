from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints

TemplateTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
TemplateContent = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]

# --- Схемы для шаблонов ответов менеджера ---

class ReplyTemplateBase(BaseModel):
    title: TemplateTitle
    content: TemplateContent

class ReplyTemplateCreate(ReplyTemplateBase):
    pass

class ReplyTemplateUpdate(BaseModel):
    title: Optional[TemplateTitle] = None
    content: Optional[TemplateContent] = None

class ReplyTemplateRead(ReplyTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
