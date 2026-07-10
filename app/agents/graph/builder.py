from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from app.agents.config.prompts import (
    BOOK_SEARCH_SYSTEM_PROMPT,
    CART_SYSTEM_PROMPT,
    CHITCHAT_SYSTEM_PROMPT,
    OFFTOPIC_SYSTEM_PROMPT,
    ORDER_LIST_SYSTEM_PROMPT,
    ORDER_STATUS_SYSTEM_PROMPT,
)
from app.agents.graph.nodes import (
    ChitChatNode,
    AgentChatNode,
    StaticReplyNode,
    should_call_tools,
)
from app.agents.graph.router import IntentRouterNode, route_by_intent
from app.agents.graph.state import STATIC_INTENTS, AgentIntentENUM, AgentState
from app.agents.smalltalk import CHITCHAT_FALLBACK_REPLIES, STATIC_INTENT_REPLIES

# node names (also used to filter streamed tokens)
ROUTER_NODE = "router"
ANSWER_NODES = {intent.value for intent in AgentIntentENUM}


def _add_tool_branch(
    graph: StateGraph,
    name: str,
    chat_model: BaseChatModel,
    system_prompt: str,
    tools: list[BaseTool],
    fallback_model: BaseChatModel | None = None,
) -> None:
    """agent node <-> its own ToolNode loop, then END."""
    tools_node_name = f"{name}_tools"

    graph.add_node(
        name,
        AgentChatNode(
            chat_model=chat_model,
            system_prompt=system_prompt,
            tools=tools,
            fallback_model=fallback_model,
        ),
    )
    graph.add_node(tools_node_name, ToolNode(tools))

    graph.add_conditional_edges(
        name,
        should_call_tools,
        {
            "tools": tools_node_name,
            "end": END,
        },
    )
    graph.add_edge(tools_node_name, name)


def build_agent_graph(
    chat_model: BaseChatModel,
    router_model: BaseChatModel,
    small_chat_model: BaseChatModel,
    book_tools: list[BaseTool],
    order_tools: list[BaseTool],
    cart_tools: list[BaseTool],
) -> CompiledStateGraph:
    """
    START -> router -> one of the branches:

      book_search  <-> book_search_tools   (RAG + exact filters)
      order_status <-> order_status_tools  (one order)
      order_list   <-> order_list_tools    (list of orders)
      cart         <-> cart_tools          (view cart, search + add to cart)
      chitchat                             (small/local model, no tools)
      offtopic                             (small/local model, no tools)
      greeting / farewell / thanks         (static reply, no LLM)

    Every branch ends at END with a final AI text answer.
    """
    get_order_tool = [t for t in order_tools if t.name == "get_order"]
    list_orders_tool = [t for t in order_tools if t.name == "list_orders"]

    graph = StateGraph(AgentState)

    graph.add_node(ROUTER_NODE, IntentRouterNode(router_model))
    graph.add_edge(START, ROUTER_NODE)

    graph.add_conditional_edges(
        ROUTER_NODE,
        route_by_intent,
        {intent.value: intent.value for intent in AgentIntentENUM},
    )

    _add_tool_branch(
        graph,
        name=AgentIntentENUM.BOOK_SEARCH.value,
        chat_model=chat_model,
        system_prompt=BOOK_SEARCH_SYSTEM_PROMPT,
        tools=book_tools,
        fallback_model=small_chat_model,
    )

    _add_tool_branch(
        graph,
        name=AgentIntentENUM.ORDER_STATUS.value,
        chat_model=chat_model,
        system_prompt=ORDER_STATUS_SYSTEM_PROMPT,
        tools=get_order_tool,
        fallback_model=small_chat_model,
    )

    _add_tool_branch(
        graph,
        name=AgentIntentENUM.ORDER_LIST.value,
        chat_model=chat_model,
        system_prompt=ORDER_LIST_SYSTEM_PROMPT,
        tools=list_orders_tool,
        fallback_model=small_chat_model,
    )

    _add_tool_branch(
        graph,
        name=AgentIntentENUM.CART.value,
        chat_model=chat_model,
        system_prompt=CART_SYSTEM_PROMPT,
        # needs search tools to resolve a title into a book id
        tools=[*cart_tools, *book_tools],
        fallback_model=small_chat_model,
    )

    # chitchat — small/local model too: persona questions and clarifications
    # don't need the big model; degrades to a canned reply on failure
    graph.add_node(
        AgentIntentENUM.CHITCHAT.value,
        ChitChatNode(
            chat_model=small_chat_model,
            system_prompt=CHITCHAT_SYSTEM_PROMPT,
            fallback_replies=CHITCHAT_FALLBACK_REPLIES,
        ),
    )
    graph.add_edge(AgentIntentENUM.CHITCHAT.value, END)

    # offtopic — cheap small/local model; degrades to a canned reply on failure
    graph.add_node(
        AgentIntentENUM.OFFTOPIC.value,
        ChitChatNode(
            chat_model=small_chat_model,
            system_prompt=OFFTOPIC_SYSTEM_PROMPT,
            fallback_replies=STATIC_INTENT_REPLIES[AgentIntentENUM.OFFTOPIC],
        ),
    )
    graph.add_edge(AgentIntentENUM.OFFTOPIC.value, END)

    # greeting / farewell / thanks — canned reply, no LLM at all
    for intent in STATIC_INTENTS:
        graph.add_node(
            intent.value,
            StaticReplyNode(replies=STATIC_INTENT_REPLIES[intent]),
        )
        graph.add_edge(intent.value, END)

    return graph.compile()
