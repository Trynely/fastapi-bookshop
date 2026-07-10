import logging
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.cache import AgentAnswerCache
from app.agents.config.base import (
    AGENT_MESSAGE_MAX_CHARS,
    AGENT_MESSAGE_TOO_LONG_MESSAGE,
    AGENT_TURN_BUSY_MESSAGE,
)
from app.agents.db.repositories.books import AgentBooksSQLAlchemyREPO
from app.agents.graph.builder import ANSWER_NODES, build_agent_graph
from app.agents.graph.state import AgentIntentENUM
from app.agents.llm import AgentLLMFactory
from app.agents.memory import RedisAgentChatHistory, ShownBooksTracker
from app.agents.ratelimit import AgentRateLimiter
from app.agents.serializers import to_tool_json
from app.agents.smalltalk import match_smalltalk
from app.agents.tools.books import build_book_tools
from app.agents.tools.cart import build_cart_tools
from app.agents.tools.orders import build_order_tools
from app.order.db.sqlalchemy.repositories.cart import CartSQLAlchemyRepository
from app.order.db.sqlalchemy.repositories.order import OrderSQLAlchemyRepository
from app.order.usecase.cart.add_item import AddBookToCart
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder

logger = logging.getLogger(__name__)

RECURSION_LIMIT = 25


class AgentChatService:
    """Assembles the per-request agent graph and streams the answer as SSE events.

    Events:
      token — next chunk of the assistant's answer text
      tool  — a tool was executed (data: tool name)
      done  — final full answer text
      error — something went wrong
    """

    def __init__(
        self,
        llm_factory: AgentLLMFactory,
        embedder: OllamaEmbedder,
        books_qdrant_repo: BooksQdrantREPO,
        agent_books_repo: AgentBooksSQLAlchemyREPO,
        order_repo: OrderSQLAlchemyRepository,
        add_to_cart_uc: AddBookToCart,
        history: RedisAgentChatHistory,
        shown_books: ShownBooksTracker | None = None,
        cart_repo: CartSQLAlchemyRepository | None = None,
        rate_limiter: AgentRateLimiter | None = None,
        answer_cache: AgentAnswerCache | None = None,
    ):
        self._llm_factory = llm_factory
        self._embedder = embedder
        self._books_qdrant_repo = books_qdrant_repo
        self._agent_books_repo = agent_books_repo
        self._order_repo = order_repo
        self._add_to_cart_uc = add_to_cart_uc
        self._history = history
        self._shown_books = shown_books
        self._cart_repo = cart_repo
        self._rate_limiter = rate_limiter
        self._answer_cache = answer_cache

    def _build_graph(self, user_id: int):
        book_tools = build_book_tools(
            embedder=self._embedder,
            books_qdrant_repo=self._books_qdrant_repo,
            agent_books_repo=self._agent_books_repo,
            shown_books=self._shown_books,
            user_id=user_id,
        )
        order_tools = build_order_tools(
            order_repo=self._order_repo,
            user_id=user_id,
        )
        cart_tools = build_cart_tools(
            add_to_cart_uc=self._add_to_cart_uc,
            user_id=user_id,
            cart_repo=self._cart_repo,
        )

        return build_agent_graph(
            chat_model=self._llm_factory.chat_model(),
            router_model=self._llm_factory.router_model(),
            small_chat_model=self._llm_factory.small_chat_model(),
            book_tools=book_tools,
            order_tools=order_tools,
            cart_tools=cart_tools,
        )

    async def stream_chat(
        self,
        user_id: int,
        message: str,
    ) -> AsyncIterator[dict]:
        # rate limit first: counts EVERY message (even refused ones),
        # so a loop spamming oversized texts still hits the limits
        if self._rate_limiter is not None:
            refusal = await self._rate_limiter.check(user_id)
            if refusal is not None:
                yield {"event": "token", "data": refusal}
                yield {"event": "done", "data": to_tool_json({"answer": refusal})}
                return

        # oversized message — polite refusal, no LLM, not saved to history
        if len(message.strip()) > AGENT_MESSAGE_MAX_CHARS:
            refusal = AGENT_MESSAGE_TOO_LONG_MESSAGE.format(
                max_chars=AGENT_MESSAGE_MAX_CHARS,
            )
            yield {"event": "token", "data": refusal}
            yield {"event": "done", "data": to_tool_json({"answer": refusal})}
            return

        if self._rate_limiter is not None:
            # one turn at a time: a burst of messages must not run in parallel
            if not await self._rate_limiter.acquire_turn(user_id):
                yield {"event": "token", "data": AGENT_TURN_BUSY_MESSAGE}
                yield {
                    "event": "done",
                    "data": to_tool_json({"answer": AGENT_TURN_BUSY_MESSAGE}),
                }
                return

        try:
            async for event in self._stream_turn(user_id, message):
                yield event
        finally:
            # released on completion, errors AND client disconnect
            if self._rate_limiter is not None:
                await self._rate_limiter.release_turn(user_id)

    async def _stream_turn(
        self,
        user_id: int,
        message: str,
    ) -> AsyncIterator[dict]:
        history = await self._history.load(user_id)
        last_assistant = next(
            (
                msg.content
                for msg in reversed(history)
                if isinstance(msg, AIMessage) and isinstance(msg.content, str)
            ),
            None,
        )

        # trivial messages (greetings, thanks, emoji) — canned reply, no LLM;
        # short answers to the assistant's question fall through to the LLM
        canned = match_smalltalk(message, last_assistant_message=last_assistant)
        if canned is not None:
            yield {"event": "token", "data": canned}
            await self._history.append(
                user_id=user_id,
                user_message=message,
                assistant_message=canned,
            )
            yield {"event": "done", "data": to_tool_json({"answer": canned})}
            return

        # a repeated question (any user) — replay the cached answer, no LLM
        if self._answer_cache is not None:
            cached = await self._answer_cache.get(message)
            if cached is not None:
                yield {"event": "token", "data": cached}
                await self._history.append(
                    user_id=user_id,
                    user_message=message,
                    assistant_message=cached,
                )
                yield {"event": "done", "data": to_tool_json({"answer": cached})}
                return

        graph = self._build_graph(user_id)

        state_input = {
            "messages": [*history, HumanMessage(content=message)],
        }

        answer_parts: list[str] = []
        answer_node = ""

        try:
            async for chunk, metadata in graph.astream(
                state_input,
                stream_mode="messages",
                config={"recursion_limit": RECURSION_LIMIT},
            ):
                node = metadata.get("langgraph_node", "")

                # tool finished (ToolNode emits ToolMessage)
                if node.endswith("_tools"):
                    tool_name = getattr(chunk, "name", None)
                    yield {
                        "event": "tool",
                        "data": to_tool_json({"name": tool_name}),
                    }
                    # a new LLM turn starts after tools
                    answer_parts.clear()
                    continue

                if node not in ANSWER_NODES:
                    continue

                # streaming models yield AIMessageChunk, others a full AIMessage
                if not isinstance(chunk, AIMessage):
                    continue

                # skip tool-call chunks, stream only answer text
                if getattr(chunk, "tool_call_chunks", None) or chunk.tool_calls:
                    continue

                if not chunk.content:
                    continue

                answer_parts.append(chunk.content)
                answer_node = node
                yield {
                    "event": "token",
                    "data": chunk.content,
                }
        except Exception:
            logger.exception("agent chat failed (user_id=%s)", user_id)
            yield {
                "event": "error",
                "data": to_tool_json({
                    "message": "Не получилось обработать запрос, попробуйте ещё раз.",
                }),
            }
            return

        answer = "".join(answer_parts)

        if answer:
            await self._history.append(
                user_id=user_id,
                user_message=message,
                assistant_message=answer,
            )

            # only self-contained book answers are shared between users
            if (
                self._answer_cache is not None
                and answer_node == AgentIntentENUM.BOOK_SEARCH.value
            ):
                await self._answer_cache.set(message, answer)

        yield {
            "event": "done",
            "data": to_tool_json({"answer": answer}),
        }
