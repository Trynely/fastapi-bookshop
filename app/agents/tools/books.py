from decimal import Decimal
from typing import Optional

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field
from qdrant_client.models import (
    FieldCondition,
    Filter,
    HasIdCondition,
    MatchValue,
)

from app.agents.config.base import (
    AGENT_FILTER_SEARCH_LIMIT,
    AGENT_RAG_SCORE_THRESHOLD,
    AGENT_RAG_SEARCH_LIMIT,
)
from app.agents.db.repositories.books import AgentBooksSQLAlchemyREPO
from app.agents.memory import ShownBooksTracker
from app.agents.serializers import book_to_dict, to_tool_json
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder


class SemanticSearchArgs(BaseModel):
    query: str = Field(
        description=(
            "Search query describing mood, theme or plot, e.g. "
            "'sad melancholic novel', 'книга про космос и одиночество'"
        ),
    )


class FilterBooksArgs(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="Part of the book title",
    )
    author_name: Optional[str] = Field(
        default=None,
        description="Author name (or part of it), e.g. 'Достоевский'",
    )
    category_name: Optional[str] = Field(
        default=None,
        description="Category name, e.g. 'IT', 'Фантастика'",
    )
    price_min: Optional[float] = Field(
        default=None,
        description="Minimum price in euros",
        ge=0,
    )
    price_max: Optional[float] = Field(
        default=None,
        description="Maximum price in euros, e.g. 20 for 'cheaper than 20 euros'",
        ge=0,
    )
    rating_min: Optional[float] = Field(
        default=None,
        description="Minimum rating from 0 to 5",
        ge=0,
        le=5,
    )


def build_book_tools(
    embedder: OllamaEmbedder,
    books_qdrant_repo: BooksQdrantREPO,
    agent_books_repo: AgentBooksSQLAlchemyREPO,
    shown_books: Optional["ShownBooksTracker"] = None,
    user_id: Optional[int] = None,
) -> list[BaseTool]:
    @tool(args_schema=SemanticSearchArgs)
    async def semantic_search_books(query: str) -> str:
        """Semantic (vector) book search by mood, theme, plot or free-form description.
        Books already recommended in this dialog are excluded automatically."""
        vector = await embedder.embed(query)

        # deterministic server-side dedup between turns:
        # exclude everything already shown — by id AND by title+author
        shown_ids: list[int] = []
        shown_keys: set[str] = set()
        if shown_books and user_id is not None:
            shown_ids, shown_keys = await shown_books.get(user_id)

        must_not = []
        if shown_ids:
            must_not.append(HasIdCondition(has_id=shown_ids))

        points = await books_qdrant_repo.get_similar(
            query=vector,
            # fetch extra points: duplicates are collapsed below
            limit=AGENT_RAG_SEARCH_LIMIT * 3,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="is_available",
                        match=MatchValue(value=True),
                    ),
                ],
                must_not=must_not,
            ),
            score_threshold=AGENT_RAG_SCORE_THRESHOLD,
        )

        if not points:
            return to_tool_json({
                "books": [],
                "message": (
                    "nothing new found — everything relevant was already "
                    "recommended in this dialog"
                    if shown_ids else "nothing found"
                ),
            })

        scores = {point.id: point.score for point in points}
        books = await agent_books_repo.get_by_ids(list(scores))

        # collapse duplicates: same title+author under different ids,
        # both inside this result AND against previously shown books
        seen: set[str] = set(shown_keys)
        unique = []
        for book in books:
            key = ShownBooksTracker.book_key(
                book.title,
                book.author.name if book.author else None,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(book)

        result = unique[:AGENT_RAG_SEARCH_LIMIT]

        if not result:
            return to_tool_json({
                "books": [],
                "message": (
                    "nothing new found — everything relevant was already "
                    "recommended in this dialog"
                ),
            })

        # remember what was shown, so 'more options' never repeats them
        if shown_books and user_id is not None:
            await shown_books.add(
                user_id,
                [
                    (
                        book.id,
                        ShownBooksTracker.book_key(
                            book.title,
                            book.author.name if book.author else None,
                        ),
                    )
                    for book in result
                ],
            )

        return to_tool_json({
            "books": [
                book_to_dict(book, score=scores.get(book.id))
                for book in result
            ],
        })

    @tool(args_schema=FilterBooksArgs)
    async def filter_books(
        title: Optional[str] = None,
        author_name: Optional[str] = None,
        category_name: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        rating_min: Optional[float] = None,
    ) -> str:
        """Exact book search by filters: title, author, category, price range, rating."""
        books = await agent_books_repo.search_by_filters(
            title=title,
            author_name=author_name,
            category_name=category_name,
            price_min=Decimal(str(price_min)) if price_min is not None else None,
            price_max=Decimal(str(price_max)) if price_max is not None else None,
            rating_min=Decimal(str(rating_min)) if rating_min is not None else None,
            limit=AGENT_FILTER_SEARCH_LIMIT,
        )

        if not books:
            return to_tool_json({"books": [], "message": "nothing found"})

        return to_tool_json({
            "books": [book_to_dict(book) for book in books],
        })

    return [semantic_search_books, filter_books]
