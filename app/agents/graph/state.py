from enum import Enum
from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentIntentENUM(str, Enum):
    # need the big chat model (generation / tools)
    BOOK_SEARCH = "book_search"
    ORDER_STATUS = "order_status"
    ORDER_LIST = "order_list"
    CART = "cart"
    CHITCHAT = "chitchat"
    # answered with a static reply — no LLM at all
    GREETING = "greeting"
    FAREWELL = "farewell"
    THANKS = "thanks"
    # answered by the small/local model (falls back to a static reply)
    OFFTOPIC = "offtopic"


# intents that get a canned reply instead of a chat-model generation
STATIC_INTENTS = frozenset({
    AgentIntentENUM.GREETING,
    AgentIntentENUM.FAREWELL,
    AgentIntentENUM.THANKS,
})


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: AgentIntentENUM
    tool_rounds: int
