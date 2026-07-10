import asyncio
import json
import uuid
from dishka import AsyncContainer, FromDishka
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.core.config.shared.redis.pubsub.listen_expired_keys import LISTEN_EXPIRED_KEYS_CHANNEL
from app.core.config.support.redis.pubsub import schat_channel, schat_user_kick_channel
from app.core.config.support.redis.keys.schat_active_msg import user_active_msg_chat_key
from app.core.db.postgres import db_helper
from app.shared.service.infrastructure.base import json_to_dict, to_json
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.responses.websoket import WSMessageTypeEnum, WSMessageActionEnum, WSMessageKeysEnum
from app.support.exceptions.chat import ChatNotFound
from app.support.exceptions.manager import ManagerAlreadyAssigned, ManagerNotFound
from app.support.exceptions.message import TooManySChatMessages
from app.support.servic import ManagerChatService
from app.support.usecase.close import CloseChatUC
from app.support.usecase.escalation import ChatEscalationUC
from app.support.usecase.manager.assign_to_chat import AssignManagerToChatUC
from app.support.usecase.manager.handle_messages import HandleManagerMessageUC
from app.support.usecase.query_handlers.filter import ChatFilterQH
from app.support.usecase.query_handlers.manager.filter import ManagerFilterQH
from app.support.usecase.query_handlers.messages.filter import ChatMessagesFilterQH
from app.client.api.dependencies import auth_user_ws
from app.client.db.postgres.models import ClientModel, ClientRoleENUM
from dishka.integrations.fastapi import inject

support_router = APIRouter(prefix="/support", tags=["Support"])

async def write_messages_to_chat(
    schat_channel: str,
    user_kick_channel: str,
    chat_session_id: str,
    chat_active_time_key: str,
    redis_pubsub: RedisPubsub,
    websocket: WebSocket,
):
    try:
        async for message in redis_pubsub.subscribe(
            schat_channel,
            user_kick_channel,
            LISTEN_EXPIRED_KEYS_CHANNEL,
        ):
            channel = message["channel"]
            data = message["data"]

            if channel == LISTEN_EXPIRED_KEYS_CHANNEL:
                if data == chat_active_time_key:
                    await websocket.close(
                        code=status.WS_1001_GOING_AWAY,
                        reason="session closed due to inactivity",
                    )
                    break
                continue

            if channel == user_kick_channel:
                if data != chat_session_id:
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="connected from another device",
                    )
                    break
                continue

            if websocket.client_state != WebSocketState.CONNECTED:
                break

            if channel == schat_channel:
                await websocket.send_text(data)
    except (asyncio.CancelledError, RuntimeError):
        pass


async def write_messages_to_manager_chat(
    redis_pubsub: RedisPubsub,
    websocket: WebSocket,
    schat_channel: str,
):
    try:
        async for message in redis_pubsub.subscribe(schat_channel):
            data = message["data"]

            if websocket.client_state != WebSocketState.CONNECTED:
                break

            await websocket.send_text(data)
    except (asyncio.CancelledError, RuntimeError):
        pass


@support_router.websocket("/ws")
@inject
async def support_chat_user_ws(
    websocket: WebSocket,
    redis_pubsub: FromDishka[RedisPubsub],
    container: FromDishka[AsyncContainer],
):
    user = await auth_user_ws(websocket)

    user_id = int(user.sub)
    chat_session_id = str(uuid.uuid4())

    await redis_pubsub.publish(
        schat_user_kick_channel(user_id),
        chat_session_id,
    )

    await websocket.accept()

    async with container() as request_container:
        chat_filter_qh = await request_container.get(ChatFilterQH)
        chat_messages_filter_qh = await request_container.get(ChatMessagesFilterQH)

        user_chat = await chat_filter_qh.get_or_create_user_chat(user_id=user_id)
        history_messages = await chat_messages_filter_qh.get_user_chat_history(
            user_id=user_id
        )
        chat_id = user_chat.id

        await websocket.send_text(
            to_json({
                WSMessageKeysEnum.TYPE: WSMessageTypeEnum.HISTORY,
                "data": {"messages": history_messages},
            })
        )

    task = asyncio.create_task(write_messages_to_chat(
        websocket=websocket,
        schat_channel=schat_channel(chat_id),
        user_kick_channel=schat_user_kick_channel(user_id),
        chat_active_time_key=user_active_msg_chat_key(user_id=user_id),
        chat_session_id=chat_session_id,
        redis_pubsub=redis_pubsub,
    ))

    try:
        while True:
            user_text = await websocket.receive_text()

            async with container() as request_container:
                close_chat_uc = await request_container.get(CloseChatUC)
                chat_escalation_uc = await request_container.get(ChatEscalationUC)

            try:
                payload = json_to_dict(user_text)
                action = payload.get(WSMessageKeysEnum.ACTION, WSMessageTypeEnum.MESSAGE)
            except json.JSONDecodeError:
                action = WSMessageTypeEnum.MESSAGE

            if action == WSMessageActionEnum.CLOSE:
                try:
                    await close_chat_uc.by_user(user_id=user_id)
                except ChatNotFound:
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="Chat not found",
                    )
                await websocket.close()
                break

            elif action == WSMessageTypeEnum.MESSAGE and user_text:
                try:
                    await chat_escalation_uc.handle_user_message(
                        user_id=user_id,
                        user_text=user_text,
                    )
                except (ChatNotFound, TooManySChatMessages) as err:
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason=err.msg,
                    )
                    break

    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@support_router.websocket("/ws/manager/{chat_id}")
@inject
async def support_chat_manager_ws(
    chat_id: int,
    websocket: WebSocket,
    redis_pubsub: FromDishka[RedisPubsub],
    container: FromDishka[AsyncContainer],
):
    auth_manager = await auth_user_ws(websocket)
    manager_id = int(auth_manager.sub)

    await websocket.accept()

    async with container() as request_container:
        assign_manager_to_chat_uc = await request_container.get(AssignManagerToChatUC)
        
        try:
            await assign_manager_to_chat_uc.execute(
                manager_id=manager_id,
                chat_id=chat_id,
            )
        except (ManagerNotFound, ChatNotFound, ManagerAlreadyAssigned) as err:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=err.msg
            )
            return

    task = asyncio.create_task(write_messages_to_manager_chat(
        websocket=websocket,
        schat_channel=schat_channel(chat_id),
        redis_pubsub=redis_pubsub,
    ))
    
    try:
        while True:
            manager_text = await websocket.receive_text()
            
            try:
                payload = json_to_dict(manager_text)
                action = payload.get(WSMessageKeysEnum.ACTION, WSMessageTypeEnum.MESSAGE)
            except json.JSONDecodeError:
                action = WSMessageTypeEnum.MESSAGE
            
            async with container() as request_container:
                close_chat_uc = await request_container.get(CloseChatUC)
                handle_manager_messages_uc = await request_container.get(HandleManagerMessageUC)

                if action == WSMessageActionEnum.CLOSE:
                    try:
                        await close_chat_uc.by_manager(chat_id=chat_id)
                    except ChatNotFound as err:
                        await websocket.close(
                            code=status.WS_1008_POLICY_VIOLATION,
                            reason=err.msg
                        )

                    await websocket.close()
                    break

                elif action == WSMessageTypeEnum.MESSAGE and manager_text:
                    try:
                        await handle_manager_messages_uc.execute(
                            chat_id=chat_id,
                            manager_text=manager_text,
                        )
                    except ChatNotFound as err:
                        await websocket.close(
                            code=status.WS_1008_POLICY_VIOLATION,
                            reason=err.msg,
                        )
                        break
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


from pydantic import BaseModel
from datetime import datetime


class ChatResponse(BaseModel):
    id: int
    user_id: int
    manager_id: int | None
    is_closed: bool
    escalation_reason: str | None
    last_message_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel
from datetime import datetime


class MessageResponse(BaseModel):
    id: int
    sender: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db.postgres import db_helper
from app.client.api.dependencies import auth_user
from app.client.db.postgres.models import ClientModel, ClientRoleENUM
from app.support.models import ChatModel


# ----------------------------
# GET manager chats
# ----------------------------

@support_router.get(
    "/manager/chats",
    response_model=list[ChatResponse],
)
async def get_manager_chats(
    status: str = Query(..., pattern="^(queue|active|closed)$"),
    payload: UserAuthorizedREQT = Depends(auth_user),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    # 🔥 Загружаем пользователя из БД
    user = await db.get(ClientModel, int(payload.sub))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.role != ClientRoleENUM.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers allowed",
        )

    chats = await ManagerChatService.get_chats(
        db=db,
        manager=user,
        status_filter=status,
    )

    return chats


# ----------------------------
# ASSIGN chat
# ----------------------------

@support_router.post(
    "/manager/chats/{chat_id}/assign",
    response_model=ChatResponse,
)
async def assign_chat(
    chat_id: int,
    payload: UserAuthorizedREQT = Depends(auth_user),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    user = await db.get(ClientModel, int(payload.sub))

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role != ClientRoleENUM.MANAGER:
        raise HTTPException(status_code=403, detail="Only managers allowed")

    chat = await ManagerChatService.assign_chat(
        db=db,
        manager=user,
        chat_id=chat_id,
    )

    return chat


# ----------------------------
# CLOSE chat
# ----------------------------

@support_router.post(
    "/manager/chats/{chat_id}/close",
    response_model=ChatResponse,
)
async def close_chat(
    chat_id: int,
    payload: UserAuthorizedREQT = Depends(auth_user),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    user = await db.get(ClientModel, int(payload.sub))

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role != ClientRoleENUM.MANAGER:
        raise HTTPException(status_code=403, detail="Only managers allowed")

    chat = await ManagerChatService.close_chat(
        db=db,
        manager=user,
        chat_id=chat_id,
    )

    return chat


@support_router.get(
    "/manager/chats/{chat_id}/messages",
    response_model=list[MessageResponse],
)
async def get_chat_history(
    chat_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    payload: UserAuthorizedREQT = Depends(auth_user),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    # 🔥 Загружаем пользователя из БД
    user = await db.get(ClientModel, int(payload.sub))

    if not user:
        raise HTTPException(401, "User not found")

    if user.role != ClientRoleENUM.MANAGER:
        raise HTTPException(403, "Only managers allowed")

    messages = await ManagerChatService.get_chat_history(
        db=db,
        manager=user,
        chat_id=chat_id,
        limit=limit,
        offset=offset,
    )

    return messages