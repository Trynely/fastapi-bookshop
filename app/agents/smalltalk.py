"""Deterministic pre-LLM filter for trivial messages.

Greetings, thanks, "ok", byes and emoji-only messages get a canned reply
straight from code — no router LLM call, no graph run.

Matching is intentionally conservative: only a whole short message may match,
so "привет, какие книги есть по Python?" still goes to the LLM.
"""

import random
import re

from app.agents.graph.state import AgentIntentENUM

# a message longer than this is never smalltalk, even if it starts with "привет"
SMALLTALK_MAX_LEN = 30

_NORMALIZE_RE = re.compile(r"[^a-zа-яё0-9\s]+")
_HAS_ALNUM_RE = re.compile(r"[a-zа-яё0-9]")
# laughter of any length: "ахаха", "хахаха", "хех", "ххх", "ahahah", "hahaha"
_LAUGHTER_RE = re.compile(r"^(?:а*х[аеих]*|a*h[aeh]*)$")

_GREETING_REPLIES = [
    "Привет! Я ассистент книжного магазина — помогу найти книгу, "
    "проверить заказ или собрать корзину. Что вас интересует?",
    "Здравствуйте! Могу порекомендовать книги, показать ваши заказы "
    "или корзину. С чего начнём?",
]
_THANKS_REPLIES = [
    "Пожалуйста! Обращайтесь, если понадобится ещё что-то по книгам или заказам.",
    "Рад помочь! Если захотите ещё что-нибудь почитать — я тут.",
]
_ACK_REPLIES = [
    "Хорошо! Если понадобится помощь с книгами или заказами — пишите.",
    "Договорились! Обращайтесь, когда захотите подобрать книгу.",
    "Отлично! Я рядом, если что-то понадобится.",
]
_HOW_ARE_YOU_REPLIES = [
    "У меня всё отлично, спасибо! Готов помочь: подобрать книгу, "
    "проверить заказ или корзину. Что вас интересует?",
    "Всё хорошо, работаю с книгами! Расскажите, что хотите почитать — "
    "жанр, автор или настроение?",
]
_BYE_REPLIES = [
    "До встречи! Заходите за новыми книгами.",
    "Всего доброго! Буду рад помочь снова.",
]
_EMOJI_REPLIES = [
    "Если нужна помощь с книгами, заказами или корзиной — просто напишите!",
]
_UNCLEAR_REPLIES = [
    "Не совсем понял вас. Могу подобрать книгу, показать заказы или "
    "корзину — что вас интересует?",
    "Кажется, сообщение оборвалось. Напишите, чем помочь: книги, "
    "заказы или корзина?",
]
_OFFTOPIC_REPLIES = [
    "Я ассистент книжного магазина и помогаю только с книгами, заказами "
    "и корзиной. Могу подобрать вам что-нибудь почитать?",
    "Это не совсем моя область — я разбираюсь в книгах и заказах нашего "
    "магазина. Хотите, порекомендую книгу?",
]

# replies for intents the router resolves without the big chat model
STATIC_INTENT_REPLIES: dict[AgentIntentENUM, list[str]] = {
    AgentIntentENUM.GREETING: _GREETING_REPLIES,
    AgentIntentENUM.FAREWELL: _BYE_REPLIES,
    AgentIntentENUM.THANKS: _THANKS_REPLIES,
    AgentIntentENUM.OFFTOPIC: _OFFTOPIC_REPLIES,
}

# used when the small model behind the chitchat branch is unavailable
CHITCHAT_FALLBACK_REPLIES = [
    "Я ИИ-ассистент книжного магазина: подбираю книги, показываю заказы "
    "и корзину. Скажите, какой жанр или автор вас интересует?",
    "Я помогаю с книгами и заказами. Расскажите, что хотите почитать — "
    "подберу варианты!",
]

_GREETINGS = {
    "привет", "приветик", "приветики", "приветствую", "приветствую вас",
    "здравствуй", "здравствуйте", "здрасте", "здрасьте",
    "добрый день", "добрый вечер", "доброе утро", "доброй ночи",
    "доброго дня", "доброго вечера", "доброго утра", "доброго времени суток",
    "здарова", "здорова", "здорово", "дарова", "дратути", "дароу",
    "салют", "салам", "салам алейкум", "ассаламу алейкум",
    "хай", "хеллоу", "хелло", "халло", "алло", "ку", "куку", "йоу", "йо",
    "hi", "hii", "hiii", "hello", "hellо", "hey", "heya", "hey there",
    "hi there", "hello there", "howdy", "yo", "sup", "wassup", "whats up",
    "good morning", "good evening", "good afternoon", "good day", "greetings",
    "morning", "evening", "afternoon",
}
_THANKS = {
    "спасибо", "спс", "спсб", "сяп", "сяпки", "благодарю", "благодарствую",
    "спасибо большое", "большое спасибо", "спасибо огромное",
    "огромное спасибо", "спасибо тебе", "спасибо вам", "спасибочки",
    "спасибки", "пасиб", "пасибо", "пасибки", "мерси", "сенкс", "сенькс",
    "от души", "красавчик", "выручил", "выручила", "помог", "помогла",
    "спасибо за помощь", "благодарю за помощь", "премного благодарен",
    "thanks", "thank you", "thank u", "thx", "tnx", "ty", "tysm",
    "thanks a lot", "thanks so much", "thank you very much",
    "thank you so much", "many thanks", "much appreciated", "appreciate it",
    "cheers",
}
_ACKS = {
    "ок", "окей", "океюшки", "окич", "ага", "угу", "ага понял", "ну ок",
    "понял", "поняла", "понятно", "все понятно", "ясно", "ясненько",
    "все ясно", "хорошо", "ладно", "ладненько", "принял", "принято",
    "договорились", "замечательно", "прекрасно", "отлично", "отличненько",
    "супер", "суперски", "класс", "классно", "круто", "кайф", "топ",
    "огонь", "шикарно", "восхитительно", "чудесно", "здорово как",
    "норм", "нормально", "пойдет", "сойдет", "годится", "подходит",
    "да", "нет", "неа", "ну да", "именно", "точно", "верно", "вот именно",
    "давай", "давайте", "конечно", "не надо", "не нужно",
    "хватит", "достаточно", "стоп", "больше не надо", "больше ничего",
    "больше не нужно", "это все", "на этом все", "пока хватит",
    "enough", "stop", "thats all", "thats it", "no more", "nothing else",
    "im done", "im good",
    "ok", "okay", "okey", "oki", "okie", "kk", "k", "got it", "gotcha",
    "understood", "roger", "noted", "fine", "alright", "all right",
    "great", "perfect", "awesome", "amazing", "excellent", "wonderful",
    "fantastic", "cool", "nice", "sweet", "neat", "lovely", "good",
    "very good", "sounds good", "yes", "yep", "yeah", "yup", "no", "nope",
    "sure", "exactly", "right", "indeed", "lol", "лол", "ахах", "ахаха",
    "хах", "хаха", "хахаха", "хех", "хехе", "кек", "ржу", "haha", "hahaha",
    "hehe", "lmao", "rofl", "xd",
}
_HOW_ARE_YOU = {
    "как дела", "как делишки", "как делищи", "как дела у тебя", "как ты",
    "как ты там", "как оно", "как сам", "как сама", "как жизнь",
    "как жизнь молодая", "как поживаешь", "как поживаете", "как настроение",
    "как успехи", "что нового", "что новенького", "чем занимаешься",
    "что делаешь", "как день проходит", "ну как ты", "все хорошо",
    "у тебя все хорошо",
    "how are you", "how are u", "how r u", "hows it going", "how is it going",
    "hows life", "hows your day", "whats new", "how are you doing",
    "how do you do", "you good", "hru", "wyd", "sup bro",
}
_BYES = {
    "пока", "покеда", "покедова", "пока пока", "давай пока", "бывай",
    "бывайте", "до свидания", "до встречи", "до скорого", "до скорой встречи",
    "до завтра", "до связи", "увидимся", "свидимся", "прощай", "прощайте",
    "всего доброго", "всего хорошего", "всех благ", "удачи", "удачи тебе",
    "удачи вам", "счастливо", "счастливого", "хорошего дня", "хорошего вечера",
    "хороших выходных", "спокойной ночи", "доброй ночи всем", "чао", "чао какао",
    "адьос", "гудбай", "байбай", "бай",
    "bye", "byе", "goodbye", "good bye", "bye bye", "byebye", "see you",
    "see ya", "cya", "see you later", "see you soon", "later", "laters",
    "take care", "farewell", "good night", "goodnight", "have a good day",
    "have a nice day", "have a good one", "ciao", "adios", "peace", "peace out",
}

# words that are ANSWERS to a question, not standalone smalltalk:
# if the assistant just asked something, they must go to the LLM with history
_CONTEXTUAL = {
    "да", "нет", "неа", "не", "ну да", "ага", "угу", "конечно", "давай",
    "давайте", "именно", "точно", "верно", "вот именно", "можно",
    "не надо", "не нужно", "хочу", "не хочу", "ок", "окей", "хорошо",
    "ладно", "первый", "второй", "третий", "первую", "вторую", "третью",
    "yes", "no", "nope", "yep", "yeah", "yup", "sure", "ok", "okay",
    "fine", "alright", "go ahead", "please do", "why not", "of course",
    "the first", "the second", "first", "second",
}

# an assistant OFFER expects an answer even without a question mark:
# "могу порекомендовать книгу по кулинарии!" + "давай" is an acceptance.
# Word boundaries matter: "захотите" must NOT match "хотите".
_OFFER_RE = re.compile(
    r"\b(могу|хотите|желаете|давайте|предлагаю|предложить"
    r"|i can|would you like|shall i|let me)\b",
    re.IGNORECASE,
)


def _expects_reply(text: str) -> bool:
    # question mark anywhere, not just the end: the question may be followed
    # by a statement ("...понравились? Так я лучше пойму ваши вкусы!");
    # "？" — full-width mark, small models sometimes leak CJK punctuation
    if "?" in text or "？" in text:
        return True

    return bool(_OFFER_RE.search(text))


_PHRASE_REPLIES: list[tuple[frozenset[str], list[str]]] = [
    (frozenset(_GREETINGS), _GREETING_REPLIES),
    (frozenset(_THANKS), _THANKS_REPLIES),
    (frozenset(_HOW_ARE_YOU), _HOW_ARE_YOU_REPLIES),
    (frozenset(_ACKS), _ACK_REPLIES),
    (frozenset(_BYES), _BYE_REPLIES),
]


def normalize_message(message: str) -> str:
    """Lowercase, drop punctuation/emoji, collapse whitespace."""
    text = _NORMALIZE_RE.sub(" ", message.lower().replace("ё", "е"))
    return " ".join(text.split())


_VOWELS = set("аеиоуыэюяaeiouy")


def _is_gibberish(normalized: str, question_pending: bool) -> bool:
    """Messages that carry no intent: "аааа", "123123123", keyboard mash."""
    compact = normalized.replace(" ", "")

    # 1-2 stray letters: "я", "аа", "фв"
    if len(compact) <= 2 and compact.isalpha():
        return True

    # one character repeated: "аааа", "яяяя", "11111"
    if len(compact) >= 3 and len(set(compact)) == 1:
        return True

    # long digit-only garbage: "123123123".
    # Short digits stay: "1" answers "какую?", "1984" is a real book query
    if compact.isdigit() and len(compact) >= 7:
        return True

    # keyboard mash without a single vowel: "фвпрлд", "sdfghj"
    if len(compact) >= 5 and compact.isalpha() and not set(compact) & _VOWELS:
        return True

    return False


def match_smalltalk(
    message: str,
    last_assistant_message: str | None = None,
) -> str | None:
    """Return a canned reply for a trivial message, or None to go to the LLM.

    If the assistant just asked a question, short answers like "да" / "нет" /
    "давай" are context-dependent and are passed through to the LLM.
    """
    stripped = message.strip()

    if not stripped or len(stripped) > SMALLTALK_MAX_LEN:
        return None

    question_pending = bool(
        last_assistant_message and _expects_reply(last_assistant_message),
    )

    # emoji / punctuation-only message ("👍", "😂😂😂", "...")
    if not _HAS_ALNUM_RE.search(stripped.lower().replace("ё", "е")):
        # "👍" right after a question is an answer, not smalltalk
        return None if question_pending else random.choice(_EMOJI_REPLIES)

    normalized = normalize_message(stripped)

    # collapse a repeated word: "бла бла бла" -> "бла", "давай давай" -> "давай"
    tokens = normalized.split()
    collapsed = len(tokens) > 1 and len(set(tokens)) == 1
    if collapsed:
        normalized = tokens[0]

    if question_pending and normalized in _CONTEXTUAL:
        return None

    if _LAUGHTER_RE.match(normalized.replace(" ", "")):
        return random.choice(_ACK_REPLIES)

    for phrases, replies in _PHRASE_REPLIES:
        if normalized in phrases:
            return random.choice(replies)

    # a repeated word that no dictionary recognized ("бла бла бла")
    if collapsed:
        return random.choice(_UNCLEAR_REPLIES)

    if _is_gibberish(normalized, question_pending):
        return random.choice(_UNCLEAR_REPLIES)

    return None
