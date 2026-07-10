# --- chat history (Redis) ---
AGENT_CHAT_HISTORY_KEY = "agent:chat:history:{user_id}"
AGENT_CHAT_HISTORY_TTL = 60 * 60  # 1h
AGENT_CHAT_HISTORY_MAX_MESSAGES = 20

# --- shown books (per-user dedup between turns, Redis) ---
AGENT_SHOWN_BOOKS_KEY = "agent:chat:shown_books:{user_id}"
AGENT_SHOWN_BOOKS_MAX = 100

# --- RAG search ---
AGENT_RAG_SEARCH_LIMIT = 5
AGENT_RAG_SCORE_THRESHOLD = 0.35

# --- exact filters search ---
AGENT_FILTER_SEARCH_LIMIT = 10

# --- orders ---
AGENT_ORDERS_LIST_LIMIT = 10

# --- graph ---
AGENT_MAX_TOOL_ROUNDS = 4

# --- message length ---
# soft limit: friendly refusal in the chat, no LLM call
AGENT_MESSAGE_MAX_CHARS = 500
AGENT_MESSAGE_TOO_LONG_MESSAGE = (
    "Сообщение получилось слишком длинным (больше {max_chars} символов). "
    "Сформулируйте, пожалуйста, короче — например, жанр, автор или "
    "номер заказа."
)
# hard limit: request validation, protects the API itself
AGENT_MESSAGE_HARD_MAX_CHARS = 10_000

# --- answer cache (Redis, shared across users) ---
AGENT_ANSWER_CACHE_KEY = "agent:chat:cache:{digest}"
AGENT_ANSWER_CACHE_TTL = 60 * 60  # 1h — catalog/prices may change
AGENT_ANSWER_CACHE_MIN_CHARS = 5

# --- one turn at a time (per user, Redis) ---
AGENT_TURN_LOCK_KEY = "agent:chat:lock:{user_id}"
AGENT_TURN_LOCK_TTL = 90  # safety net for stuck locks, seconds
AGENT_TURN_BUSY_MESSAGE = (
    "Подождите, пожалуйста — я ещё отвечаю на предыдущее сообщение."
)

# --- rate limiting (per user, Redis) ---
AGENT_RATE_LIMIT_KEY = "agent:chat:rl:{user_id}:{window}"
# window name -> (max messages, window seconds, refusal message)
AGENT_RATE_LIMITS: dict[str, tuple[int, int, str]] = {
    "minute": (
        10,
        60,
        "Вы отправляете сообщения слишком часто. Попробуйте через минуту.",
    ),
    "hour": (
        100,
        60 * 60,
        "Вы превысили лимит сообщений на этот час. Попробуйте позже.",
    ),
    "day": (
        500,
        60 * 60 * 24,
        "Вы превысили дневной лимит сообщений. Возвращайтесь завтра!",
    ),
}
