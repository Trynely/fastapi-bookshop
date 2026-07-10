import asyncio
from collections import defaultdict
from app.core.db.clickhouse import get_clickhouse_client

FLUSH_INTERVAL = 5

class PopularityBatcher:
    def __init__(self):
        self.buffer = defaultdict(lambda: {
            "total_sales": 0,
            "wishlist": 0,
            "total_ratings": 0,
            "rating_sum": 0.0,
            "rating_count": 0,
        })

    async def add_event(self, event: dict):
        book = self.buffer[int(event["book_id"])]

        match event["event"]:
            case "BOOK_SOLD":
                book["total_sales"] += event.get("delta", 1)

            case "BOOK_WISHLISTED":
                book["wishlist"] += event.get("delta", 1)

            case "BOOK_REVIEWED":
                book["total_ratings"] += 1
                book["rating_sum"] += float(event["rating"])
                book["rating_count"] += 1

    async def flush(self):
        if not self.buffer:
            return

        client = get_clickhouse_client()

        rows = [
            (
                book_id,
                data["total_sales"],
                data["wishlist"],
                data["total_ratings"],
                data["rating_sum"],
                data["rating_count"],
            )
            for book_id, data in self.buffer.items()
        ]

        client.insert(
            "book_popularity",
            rows,
            column_names=[
                "book_id",
                "total_sales",
                "wishlist",
                "total_ratings",
                "rating_sum",
                "rating_count",
            ],
        )

        self.buffer.clear()


async def periodic_flush(batcher: PopularityBatcher) -> None:
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)
        
        try:
            await batcher.flush()
        except Exception:
            pass
