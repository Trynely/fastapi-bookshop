from dataclasses import dataclass

class BookRoutersCacheKeysCONF:
    prefix = "books"

    @classmethod
    def _with_cursor(cls, base: str, cursor: str | None) -> str:
        if not cursor:
            return base
        return f"{base}:cursor:{cursor}"

    @classmethod
    def detail(cls, *args, **kwargs) -> str:
        try:
            slug = kwargs["book_slug"]
        except KeyError:
            slug = args[1]

        return f"{cls.prefix}:detail:{slug}"

    @classmethod
    def by_new(cls, *args, **kwargs) -> str:
        pagination = kwargs.get("pagination")

        cursor = (
            pagination.id_cursor
            if pagination and pagination.id_cursor
            else None
        )

        return cls._with_cursor(f"{cls.prefix}:new", cursor)

    @classmethod
    def by_popular(cls, *args, **kwargs) -> str:
        pagination = kwargs.get("pagination")

        cursor = (
            pagination.encoded_cursor[-10:]
            if pagination and pagination.encoded_cursor
            else None
        )

        return cls._with_cursor(f"{cls.prefix}:popular", cursor)
    

@dataclass(frozen=True, slots=True)
class BookRouterTTLCacheConf:
    detail_router: int = 300
    by_new_router: int = 300
    by_popular_router: int = 60

book_router_ttl_cache_conf = BookRouterTTLCacheConf()