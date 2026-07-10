from app.core.container import create_dishka_container
from functools import cache

@cache
def get_container():
    return create_dishka_container()