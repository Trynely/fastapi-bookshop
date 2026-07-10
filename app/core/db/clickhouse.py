import clickhouse_connect
from functools import lru_cache

@lru_cache(maxsize=1)
def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host="clickhouse",
        port=8123,
        database="analytics",
        username="default",
        password="",
        compress=True,
    )