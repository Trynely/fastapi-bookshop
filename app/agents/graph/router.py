import logging
import warnings

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.config.prompts import ROUTER_SYSTEM_PROMPT
from app.agents.graph.state import AgentIntentENUM, AgentState

logger = logging.getLogger(__name__)

ROUTER_CONTEXT_MESSAGES = 4
ROUTER_MESSAGE_MAX_CHARS = 300  # keep the classifier input tiny and fast

# known harmless warning from langchain-openai structured output:
# the parsed pydantic object is serialized into the message generation
warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings",
)


class RouteDecision(BaseModel):
    """Intent of the last user message."""

    intent: AgentIntentENUM = Field(
        description="Intent of the last user message",
    )


class IntentRouterNode:
    """Classifies the user's intent with a small/cheap LLM (router model)."""

    def __init__(self, router_model: BaseChatModel):
        self._classifier = router_model.with_structured_output(RouteDecision)

    @staticmethod
    def _trim(message: BaseMessage) -> BaseMessage:
        content = message.content

        if isinstance(content, str) and len(content) > ROUTER_MESSAGE_MAX_CHARS:
            message = message.model_copy(
                update={"content": content[:ROUTER_MESSAGE_MAX_CHARS] + "…"},
            )

        return message

    async def __call__(self, state: AgentState) -> dict:
        recent = [
            self._trim(message)
            for message in state["messages"][-ROUTER_CONTEXT_MESSAGES:]
        ]

        try:
            decision: RouteDecision = await self._classifier.ainvoke(
                [SystemMessage(content=ROUTER_SYSTEM_PROMPT), *recent],
            )
            intent = decision.intent
        except Exception as exc:
            # fail-safe: degrade to plain dialog instead of erroring out
            logger.warning("intent router failed (%s), fallback to chitchat", exc)
            intent = AgentIntentENUM.CHITCHAT

        return {"intent": intent, "tool_rounds": 0}


def route_by_intent(state: AgentState) -> str:
    return state["intent"].value
