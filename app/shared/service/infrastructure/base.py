import datetime
from decimal import Decimal
import json
from typing import (
    TypeVar,
    Type,
    Any,
)
from uuid import UUID

E = TypeVar("E", bound=BaseException)

async def is_exists(obj, exception: Type[E]):
    result = await obj

    if result is None:
        raise exception

    return result


def str_to_bytes(data: str):
    return data.encode("utf-8")


def get_all_subclasses(cls: type) -> set[type]:
    subclasses = set(cls.__subclasses__())

    for subclass in cls.__subclasses__():
        subclasses.update(get_all_subclasses(subclass))
    return subclasses


from dataclasses import asdict, fields, is_dataclass

def copy_fields_from_model_to_entity(model, entity, exclude:set[str]=None):
    """
        Копирует поля из SQLAlchemy модели -> dataclass entity
    """
    
    exclude = exclude or set()
    data = {}
    
    for field in fields(entity):
        if field.name not in exclude and hasattr(model, field.name):
            data[field.name] = getattr(model, field.name)
    return entity(**data)


def copy_fields_from_entity_to_model(entity, model, exclude: set[str] = None):
    """
        Копирует поля из dataclass entity -> SQLAlchemy модель
    """
    
    exclude = exclude or set()
    data = {}
    
    for name, value in vars(entity).items():
        if not name.startswith("_") and name not in exclude and hasattr(model, name):
            data[name] = value
    return model(**data)


def to_json(payload: Any, **kwargs) -> str:
    kwargs.setdefault('ensure_ascii', False)
    return json.dumps(payload, **kwargs)


def json_to_dict(payload: Any) -> json:
    return json.loads(payload)


def dataclass_to_dict(value: Any) -> Any:
    """
    Безопасная сериализация dataclass/object -> dict/json-compatible.

    Поддерживает:
    - dataclass
    - datetime
    - UUID
    - Decimal
    - list/tuple/set
    - nested structures
    """

    if is_dataclass(value):
        return {
            key: json_to_dict(val)
            for key, val in asdict(value).items()
        }

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, dict):
        return {
            key: json_to_dict(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [json_to_dict(v) for v in value]

    return value