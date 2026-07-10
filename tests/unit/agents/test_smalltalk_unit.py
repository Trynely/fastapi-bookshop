import pytest

from app.agents.smalltalk import match_smalltalk


@pytest.mark.parametrize(
    "message",
    [
        "привет",
        "Привет!",
        "Здравствуйте",
        "спасибо",
        "Спасибо большое!",
        "ок",
        "окей",
        "пока",
        "До свидания",
        "👍",
        "😂😂😂",
        "...",
        "thanks",
        "hello",
        "Здрасьте",
        "доброго дня",
        "мерси",
        "норм",
        "лол",
        "ахахах",
        "hahaha",
        "чао",
        "see ya",
        "kk",
        "как делишки",
        "Как дела?",
        "как жизнь",
        "что нового?",
        "how are you",
        "хватит",
        "достаточно",
        "стоп",
        "это всё",
        "я",
        "ю",
        "аааа",
        "яяяяяя",
        ".....",
        ")))))))",
        "123123123",
        "фвпрлд",
        "sdfghj",
        "бла бла бла",
        "ла ла ла",
    ],
)
def test_trivial_message_gets_canned_reply(message: str):
    assert match_smalltalk(message) is not None


@pytest.mark.parametrize(
    "message",
    [
        "какие книги есть по Python?",
        "опиши книгу Гарри Поттер",
        "привет, покажи мои заказы",
        "спасибо, а что в корзине?",
        "где мой заказ?",
        "добавь в корзину",
        "как дела с заказом?",
        "хватит искать, покажи корзину",
        "1984",
        "451",
        "гарри поттер",
        "",
        "   ",
    ],
)
def test_real_query_goes_to_llm(message: str):
    assert match_smalltalk(message) is None


QUESTION = "Что-то из этого заинтересовало или ищем что-то другое?"
STATEMENT = "Хорошо! Если понадобится помощь с книгами — пишите."


@pytest.mark.parametrize(
    "message",
    ["да", "нет", "давай", "конечно", "👍", "первую", "ок"],
)
def test_answer_to_pending_question_goes_to_llm(message: str):
    assert match_smalltalk(message, last_assistant_message=QUESTION) is None


@pytest.mark.parametrize("message", ["да", "нет", "давай", "ок"])
def test_contextual_word_without_question_is_canned(message: str):
    assert match_smalltalk(message, last_assistant_message=STATEMENT) is not None
    assert match_smalltalk(message, last_assistant_message=None) is not None


@pytest.mark.parametrize("message", ["спасибо", "привет", "пока", "ахаха"])
def test_context_free_smalltalk_ignores_pending_question(message: str):
    assert match_smalltalk(message, last_assistant_message=QUESTION) is not None


OFFER = (
    "Рецепты — это за пределами моих обязанностей, "
    "но я могу порекомендовать книгу по кулинарии!"
)
NON_OFFER = "Договорились! Обращайтесь, когда захотите подобрать книгу."


@pytest.mark.parametrize("message", ["давай", "да", "нет", "конечно"])
def test_answer_to_offer_without_question_mark_goes_to_llm(message: str):
    assert match_smalltalk(message, last_assistant_message=OFFER) is None


@pytest.mark.parametrize("message", ["давай", "да", "ок"])
def test_zahotite_is_not_an_offer(message: str):
    assert match_smalltalk(message, last_assistant_message=NON_OFFER) is not None
