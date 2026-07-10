from langchain_openai import ChatOpenAI

from app.core.config.base import Settings


class AgentLLMFactory:
    """Builds chat models from FASTAPI__LLM__* settings (OpenAI-compatible API)."""

    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def _router_base_url(self) -> str:
        return self._settings.llm.router_base_url or self._settings.llm.base_url

    @property
    def _router_api_key(self) -> str:
        return self._settings.llm.router_api_key or self._settings.llm.api_key

    def chat_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            base_url=self._settings.llm.base_url,
            api_key=self._settings.llm.api_key,
            model=self._settings.llm.chat_model,
            streaming=True,
            # provider cold-start can hang the first request for ~2 min,
            # while a retry lands on the warm path in seconds —
            # so fail fast and retry instead of waiting
            timeout=30,
            max_retries=2,
        )

    def small_chat_model(self) -> ChatOpenAI:
        # cheap/local model (same as the router) used to GENERATE short replies
        # for lightweight branches (offtopic) — the big model is not worth it there
        return ChatOpenAI(
            base_url=self._router_base_url,
            api_key=self._router_api_key,
            model=(
                self._settings.llm.small_chat_model
                or self._settings.llm.router_model
            ),
            streaming=True,
            timeout=15,
            max_retries=1,
        )

    def router_model(self) -> ChatOpenAI:
        # router must be FAST: short timeout, no retries —
        # on failure the graph degrades to the chitchat branch
        return ChatOpenAI(
            base_url=self._router_base_url,
            api_key=self._router_api_key,
            model=self._settings.llm.router_model,
            timeout=10,
            max_retries=1,  # one quick retry to skip the cold-start hang
        )
