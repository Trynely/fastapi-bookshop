from app.support.models import ChatMessageSender, EscalationReason


class EscalationReasonFilter:
    title = "Escalation Reason"
    parameter_name = "escalation_reason"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            (reason.value, reason.value.replace("_", " ").capitalize())
            for reason in EscalationReason
        ]

    async def get_filtered_query(self, stmt, value, model):
        if value:
            stmt = stmt.where(model.escalation_reason == value)

        return stmt


class MessageSenderFilter:
    title = "Sender"
    parameter_name = "sender"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            (sender.value, sender.value.capitalize())
            for sender in ChatMessageSender
        ]

    async def get_filtered_query(self, stmt, value, model):
        if value:
            stmt = stmt.where(model.sender == value)

        return stmt
