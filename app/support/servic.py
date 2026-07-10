from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.support.models import ChatModel, ChatMessageModel


from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.support.models import ChatModel
from app.client.db.postgres.models import ClientModel, ClientRoleENUM


class ManagerChatService:

    @staticmethod
    async def get_chats(
        db: AsyncSession,
        manager: ClientModel,
        status_filter: str
    ):
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(status_code=403, detail="Forbidden")

        query = select(ChatModel)

        if status_filter == "queue":
            query = query.where(
                and_(
                    ChatModel.manager_id.is_(None),
                    ChatModel.is_closed.is_(False),
                )
            )

        elif status_filter == "active":
            query = query.where(
                and_(
                    ChatModel.manager_id == manager.id,
                    ChatModel.is_closed.is_(False),
                )
            )

        elif status_filter == "closed":
            query = query.where(
                ChatModel.is_closed.is_(True)
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid status filter"
            )

        result = await db.scalars(query.order_by(ChatModel.last_message_at.desc()))
        return result.all()

    @staticmethod
    async def assign_chat(
        db: AsyncSession,
        manager: ClientModel,
        chat_id: int
    ):
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(status_code=403, detail="Forbidden")

        chat = await db.get(ChatModel, chat_id)

        if not chat or chat.is_closed:
            raise HTTPException(status_code=404, detail="Chat not found")

        if chat.manager_id and chat.manager_id != manager.id:
            raise HTTPException(
                status_code=409,
                detail="Chat already assigned"
            )

        chat.assign_manager(manager.id)
        await db.commit()
        await db.refresh(chat)

        return chat

    @staticmethod
    async def close_chat(
        db: AsyncSession,
        manager: ClientModel,
        chat_id: int
    ):
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(status_code=403, detail="Forbidden")

        chat = await db.get(ChatModel, chat_id)

        if not chat or chat.is_closed:
            raise HTTPException(status_code=404, detail="Chat not found")

        if chat.manager_id != manager.id:
            raise HTTPException(
                status_code=403,
                detail="Not your chat"
            )

        chat.close()
        await db.commit()
        await db.refresh(chat)

        return chat
    
    @staticmethod
    async def get_chat_history(
        db,
        manager,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ):
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(403, "Forbidden")

        chat = await db.get(ChatModel, chat_id)

        if not chat:
            raise HTTPException(404, "Chat not found")

        # Менеджер может смотреть:
        # 1. Свои чаты
        # 2. Чаты в очереди (manager_id is None)

        if chat.manager_id and chat.manager_id != manager.id:
            raise HTTPException(403, "Not your chat")

        query = (
            select(ChatMessageModel)
            .where(ChatMessageModel.chat_id == chat_id)
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.scalars(query)

        return result.all()