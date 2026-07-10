from pydantic import BaseModel, Field

from app.agents.config.base import AGENT_MESSAGE_HARD_MAX_CHARS


class AgentChatREQT(BaseModel):
    # the hard cap only protects the transport; the soft, user-friendly
    # limit (AGENT_MESSAGE_MAX_CHARS) is enforced in the service so the
    # user gets a polite chat reply instead of a 422
    message: str = Field(
        min_length=1,
        max_length=AGENT_MESSAGE_HARD_MAX_CHARS,
        description="Сообщение пользователя агенту-консультанту",
    )
