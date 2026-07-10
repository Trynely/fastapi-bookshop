import logging
import random

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.config.base import AGENT_MAX_TOOL_ROUNDS
from app.agents.graph.state import AgentState

logger = logging.getLogger(__name__)


class AgentChatNode:
    """One graph branch: LLM with a system prompt and its own tool set.

    The LLM decides whether to call tools; after AGENT_MAX_TOOL_ROUNDS
    rounds tools are no longer offered, forcing a final text answer.

    With `fallback_model` set (a local tool-capable model), a failure of
    the primary provider (quota, outage) degrades to the fallback instead
    of erroring out the whole turn.
    """

    def __init__(
        self,
        chat_model: BaseChatModel,
        system_prompt: str,
        tools: list[BaseTool],
        fallback_model: BaseChatModel | None = None,
    ):
        self._model = chat_model
        self._model_with_tools = chat_model.bind_tools(tools)
        self._fallback = fallback_model
        self._fallback_with_tools = (
            fallback_model.bind_tools(tools) if fallback_model else None
        )
        self._system_prompt = system_prompt

    async def __call__(self, state: AgentState) -> dict:
        rounds = state.get("tool_rounds", 0)
        with_tools = rounds < AGENT_MAX_TOOL_ROUNDS

        model = self._model_with_tools if with_tools else self._model
        messages = [SystemMessage(content=self._system_prompt), *state["messages"]]

        try:
            response: AIMessage = await model.ainvoke(messages)
        except Exception:
            if self._fallback is None:
                raise
            logger.warning(
                "primary chat model failed, degrading to fallback model",
                exc_info=True,
            )
            fallback = self._fallback_with_tools if with_tools else self._fallback
            response = await fallback.ainvoke(messages)

        return {
            "messages": [response],
            "tool_rounds": rounds + 1,
        }


class StaticReplyNode:
    """Canned-reply branch: greeting/farewell/thanks/offtopic — no LLM at all."""

    def __init__(self, replies: list[str]):
        self._replies = replies

    async def __call__(self, state: AgentState) -> dict:
        return {"messages": [AIMessage(content=random.choice(self._replies))]}


class ChitChatNode:
    """Plain dialog branch: no tools, just the shop persona.

    With `fallback_replies` set (e.g. the offtopic branch on a small/local
    model) a model failure degrades to a canned reply instead of an error.
    """

    def __init__(
        self,
        chat_model: BaseChatModel,
        system_prompt: str,
        fallback_replies: list[str] | None = None,
    ):
        self._model = chat_model
        self._system_prompt = system_prompt
        self._fallback_replies = fallback_replies

    async def __call__(self, state: AgentState) -> dict:
        try:
            response = await self._model.ainvoke(
                [SystemMessage(content=self._system_prompt), *state["messages"]],
            )
        except Exception:
            if self._fallback_replies is None:
                raise
            logger.warning("chitchat model failed, using canned reply", exc_info=True)
            response = AIMessage(content=random.choice(self._fallback_replies))

        return {"messages": [response]}


def should_call_tools(state: AgentState) -> str:
    """After an agent node: run its tools or finish."""
    last = state["messages"][-1]

    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"

    return "end"
