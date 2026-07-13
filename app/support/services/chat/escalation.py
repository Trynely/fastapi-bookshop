from app.support.models import ChatModel, EscalationReason
import re

# сравниваем с text.lower() по началу слова, поэтому ключи — основы слов в нижнем регистре
OPERATOR_KEYWORDS = ["оператор", "человек", "менеджер", "живой"]
COMPLEX_KEYWORDS = ["оплат", "возврат", "жалоб", "заказ", "деньг", "денег", "о боже", "боже мой"]
PROFANITY_WORDS = ["бляд", "хуй", "сука", "блять"]

def detect_chat_escalation(text: str) -> EscalationReason | None:
    text_lower = text.lower()

    # матчим по началу слова, чтобы ловить склонения: "оператора", "с оплатой"
    for word in OPERATOR_KEYWORDS:
        if re.search(rf"\b{word}", text_lower):
            return EscalationReason.OPERATOR_REQUEST

    for word in COMPLEX_KEYWORDS:
        if re.search(rf"\b{word}", text_lower):
            return EscalationReason.COMPLEX_CASE

    for word in PROFANITY_WORDS:
        if re.search(word, text_lower):
            return EscalationReason.PROFANITY

    return None


def chat_is_escalated(chat: ChatModel) -> bool:
    return chat.escalation_reason is not None


def escalate_chat(chat: ChatModel, reason: EscalationReason):
    chat.escalation_reason = reason