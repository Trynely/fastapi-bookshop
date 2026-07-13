from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.db.postgres.models import ClientModel, ClientRoleENUM
from app.support.models import ChatMessageModel, ChatModel
from app.support.services.chat.assign_manager import assign_manager_to_chat
from app.support.services.chat.close import close_chat


class ManagerChatService:

    @staticmethod
    async def get_chats(
        db: AsyncSession,
        manager: ClientModel,
        status_filter: str,
    ) -> list[ChatModel]:
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        query = select(ChatModel)

        if status_filter == "queue":
            query = query.where(
                ChatModel.manager_id.is_(None),
                ChatModel.is_closed.is_(False),
            )

        elif status_filter == "active":
            query = query.where(
                ChatModel.manager_id == manager.id,
                ChatModel.is_closed.is_(False),
            )

        elif status_filter == "closed":
            query = query.where(ChatModel.is_closed.is_(True))

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status filter",
            )

        result = await db.scalars(query.order_by(ChatModel.last_message_at.desc()))
        return result.all()

    @staticmethod
    async def assign_chat(
        db: AsyncSession,
        manager: ClientModel,
        chat_id: int,
    ) -> ChatModel:
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        chat = await db.get(ChatModel, chat_id)

        if not chat or chat.is_closed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )

        if chat.manager_id and chat.manager_id != manager.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat already assigned",
            )

        assign_manager_to_chat(chat=chat, manager_id=manager.id)
        await db.commit()
        await db.refresh(chat)

        return chat

    @staticmethod
    async def close_chat(
        db: AsyncSession,
        manager: ClientModel,
        chat_id: int,
    ) -> ChatModel:
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        chat = await db.get(ChatModel, chat_id)

        if not chat or chat.is_closed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )

        if chat.manager_id != manager.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your chat",
            )

        close_chat(chat)
        await db.commit()
        await db.refresh(chat)

        return chat

    @staticmethod
    async def get_chat_history(
        db: AsyncSession,
        manager: ClientModel,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessageModel]:
        if manager.role != ClientRoleENUM.MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        chat = await db.get(ChatModel, chat_id)

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )

        # Менеджер может смотреть свои чаты и чаты в очереди (manager_id is None)
        if chat.manager_id and chat.manager_id != manager.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your chat",
            )

        query = (
            select(ChatMessageModel)
            .where(ChatMessageModel.chat_id == chat_id)
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.scalars(query)
        return result.all()
