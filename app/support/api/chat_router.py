import asyncio
import json
import uuid

from dishka import AsyncContainer, FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Query, Response, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.api.dependencies import auth_user_ws
from app.client.api.responses.jwt.access import JwtAccessTokenRESP
from app.client.db.postgres.models import ClientModel
from app.core.config.client.jwt.httponly_cookie import JWT_REFRESH_COOKIE_CONF
from app.core.config.client.jwt.roles import AUTHORIZED_MANAGER, AUTHORIZED_USER
from app.core.config.shared.redis.pubsub.listen_expired_keys import LISTEN_EXPIRED_KEYS_CHANNEL
from app.core.config.support.redis.cache.user_schat import chat_schat_cache_key, user_chat_cache_key
from app.core.config.support.redis.keys.schat_active_msg import user_active_msg_chat_key
from app.core.config.support.redis.keys.schat_manager_lock import SCHAT_MANAGER_LOCK_TTL, schat_manager_lock_key
from app.core.config.support.redis.pubsub import schat_channel, schat_user_kick_channel
from app.core.db.postgres import db_helper
from app.shared.service.infrastructure.base import json_to_dict, to_json
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.dependencies import get_current_manager
from app.support.api.requests.manager_login import ManagerLoginREQT
from app.support.api.responses.chat import ChatMessageRead, ChatRead
from app.support.api.responses.templates import (
    ReplyTemplateCreate,
    ReplyTemplateRead,
    ReplyTemplateUpdate,
)
from app.support.api.responses.websoket import WSMessageActionEnum, WSMessageKeysEnum, WSMessageTypeEnum
from app.support.exceptions.chat import ChatNotFound
from app.support.exceptions.manager import (
    ManagerAlreadyAssigned,
    ManagerAlreadyConnected,
    ManagerNotAssigned,
    ManagerNotFound,
)
from app.support.exceptions.message import SChatUserMuted, TooManySChatMessages
from app.support.service import ManagerChatService, ManagerReplyTemplateService
from app.support.usecase.close import CloseChatUC
from app.support.usecase.escalation import ChatEscalationUC
from app.support.usecase.manager.assign_to_chat import AssignManagerToChatUC
from app.support.usecase.manager.handle_messages import HandleManagerMessageUC
from app.support.usecase.manager.leave_chat import ManagerLeaveChatUC
from app.support.usecase.manager.login import ManagerLoginUC
from app.support.usecase.query_handlers.filter import ChatFilterQH
from app.support.usecase.query_handlers.messages.filter import ChatMessagesFilterQH

support_router = APIRouter(prefix="/support", tags=["Support"])


def extract_ws_action(raw_text: str) -> str:
    """Клиент шлёт либо сырой текст (обычное сообщение), либо JSON вида {"action": ...}."""
    try:
        payload = json_to_dict(raw_text)
    except json.JSONDecodeError:
        return WSMessageTypeEnum.MESSAGE

    if not isinstance(payload, dict):
        return WSMessageTypeEnum.MESSAGE

    return payload.get(WSMessageKeysEnum.ACTION, WSMessageTypeEnum.MESSAGE)


async def write_messages_to_chat(
    chat_channel: str,
    user_kick_channel: str,
    chat_session_id: str,
    chat_active_time_key: str,
    redis_pubsub: RedisPubsub,
    websocket: WebSocket,
):
    try:
        async for message in redis_pubsub.subscribe(
            chat_channel,
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

            if channel == chat_channel:
                await websocket.send_text(data)
    except (asyncio.CancelledError, RuntimeError):
        pass


async def write_messages_to_manager_chat(
    redis_pubsub: RedisPubsub,
    websocket: WebSocket,
    chat_channel: str,
):
    try:
        async for message in redis_pubsub.subscribe(chat_channel):
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

    if user.role != AUTHORIZED_USER:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="user role required",
        )
        return

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
        chat_channel=schat_channel(chat_id),
        user_kick_channel=schat_user_kick_channel(user_id),
        chat_active_time_key=user_active_msg_chat_key(user_id=user_id),
        chat_session_id=chat_session_id,
        redis_pubsub=redis_pubsub,
    ))

    try:
        while True:
            user_text = await websocket.receive_text()
            action = extract_ws_action(user_text)

            async with container() as request_container:
                if action == WSMessageActionEnum.CLOSE:
                    close_chat_uc = await request_container.get(CloseChatUC)

                    try:
                        await close_chat_uc.by_user(user_id=user_id)
                    except ChatNotFound:
                        pass

                    await websocket.close()
                    break

                elif action == WSMessageTypeEnum.MESSAGE and user_text:
                    chat_escalation_uc = await request_container.get(ChatEscalationUC)

                    try:
                        await chat_escalation_uc.handle_user_message(
                            user_id=user_id,
                            user_text=user_text,
                        )
                    except ChatNotFound as err:
                        await websocket.close(
                            code=status.WS_1008_POLICY_VIOLATION,
                            reason=err.msg,
                        )
                        break
                    except (TooManySChatMessages, SChatUserMuted) as err:
                        await websocket.send_text(
                            to_json({
                                WSMessageKeysEnum.TYPE: WSMessageTypeEnum.ERROR,
                                "data": err.msg,
                            })
                        )

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
    redis_keyspace: FromDishka[RedisClient],
    container: FromDishka[AsyncContainer],
):
    auth_manager = await auth_user_ws(websocket)

    if auth_manager.role != AUTHORIZED_MANAGER:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="manager role required",
        )
        return

    manager_id = int(auth_manager.sub)

    manager_session_id = str(uuid.uuid4())
    manager_lock_key = schat_manager_lock_key(chat_id)

    await websocket.accept()

    lock_acquired = await redis_keyspace.string.add(
        manager_lock_key,
        manager_session_id,
        ex=SCHAT_MANAGER_LOCK_TTL,
        nx=True,
    )
    if not lock_acquired:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=ManagerAlreadyConnected.msg,
        )
        return

    task = None
    try:
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
            chat_channel=schat_channel(chat_id),
            redis_pubsub=redis_pubsub,
        ))

        while True:
            manager_text = await websocket.receive_text()
            action = extract_ws_action(manager_text)

            async with container() as request_container:
                if action == WSMessageActionEnum.CLOSE:
                    close_chat_uc = await request_container.get(CloseChatUC)

                    try:
                        await close_chat_uc.by_manager(chat_id=chat_id)
                    except ChatNotFound:
                        pass

                    await websocket.close()
                    break

                elif action == WSMessageActionEnum.LEAVE:
                    manager_leave_chat_uc = await request_container.get(ManagerLeaveChatUC)

                    try:
                        await manager_leave_chat_uc.execute(
                            manager_id=manager_id,
                            chat_id=chat_id,
                        )
                    except (ChatNotFound, ManagerNotAssigned) as err:
                        await websocket.close(
                            code=status.WS_1008_POLICY_VIOLATION,
                            reason=err.msg,
                        )
                    else:
                        await websocket.close()
                    break

                elif action == WSMessageTypeEnum.MESSAGE and manager_text:
                    handle_manager_messages_uc = await request_container.get(HandleManagerMessageUC)

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
        lock_owner = await redis_keyspace.string.get(manager_lock_key)
        if isinstance(lock_owner, bytes):
            lock_owner = lock_owner.decode()
        if lock_owner == manager_session_id:
            await redis_keyspace.key.remove(manager_lock_key)

        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@support_router.post(
    "/manager/login",
    response_model=JwtAccessTokenRESP,
    summary="Вход Менеджера Поддержки",
)
@inject
async def manager_login(
    body: ManagerLoginREQT,
    response: Response,
    manager_login_uc: FromDishka[ManagerLoginUC],
):
    jwt = await manager_login_uc.execute(body)

    response.set_cookie(**JWT_REFRESH_COOKIE_CONF, value=jwt.refresh_token)
    return JwtAccessTokenRESP(access_token=jwt.access_token)


@support_router.get(
    "/manager/chats",
    response_model=list[ChatRead],
)
async def get_manager_chats(
    status_filter: str = Query(..., alias="status", pattern="^(queue|active|closed)$"),
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    return await ManagerChatService.get_chats(
        db=db,
        manager=user,
        status_filter=status_filter,
    )


@support_router.post(
    "/manager/chats/{chat_id}/assign",
    response_model=ChatRead,
)
@inject
async def assign_chat(
    chat_id: int,
    redis_keyspace: FromDishka[RedisClient],
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    chat = await ManagerChatService.assign_chat(
        db=db,
        manager=user,
        chat_id=chat_id,
    )

    # у пользователя закэширован чат без менеджера — сбрасываем
    await redis_keyspace.key.remove(user_chat_cache_key(chat.user_id))

    return chat


@support_router.post(
    "/manager/chats/{chat_id}/close",
    response_model=ChatRead,
)
@inject
async def close_chat(
    chat_id: int,
    redis_keyspace: FromDishka[RedisClient],
    redis_pubsub: FromDishka[RedisPubsub],
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    chat = await ManagerChatService.close_chat(
        db=db,
        manager=user,
        chat_id=chat_id,
    )

    await redis_keyspace.key.remove(user_chat_cache_key(chat.user_id))
    await redis_keyspace.key.remove(chat_schat_cache_key(chat.id))

    await redis_pubsub.publish(schat_channel(chat.id), {
        WSMessageKeysEnum.TYPE: WSMessageTypeEnum.SYSTEM,
        "data": "chat is closed by manager",
    })

    return chat


@support_router.get(
    "/manager/templates",
    response_model=list[ReplyTemplateRead],
)
async def get_reply_templates(
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    return await ManagerReplyTemplateService.get_templates(db=db, manager=user)


@support_router.post(
    "/manager/templates",
    response_model=ReplyTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reply_template(
    body: ReplyTemplateCreate,
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    return await ManagerReplyTemplateService.create_template(
        db=db,
        manager=user,
        data=body,
    )


@support_router.patch(
    "/manager/templates/{template_id}",
    response_model=ReplyTemplateRead,
)
async def update_reply_template(
    template_id: int,
    body: ReplyTemplateUpdate,
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    return await ManagerReplyTemplateService.update_template(
        db=db,
        manager=user,
        template_id=template_id,
        data=body,
    )


@support_router.delete(
    "/manager/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reply_template(
    template_id: int,
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    await ManagerReplyTemplateService.delete_template(
        db=db,
        manager=user,
        template_id=template_id,
    )


@support_router.get(
    "/manager/chats/{chat_id}/messages",
    response_model=list[ChatMessageRead],
)
async def get_chat_history(
    chat_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: ClientModel = Depends(get_current_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
):
    return await ManagerChatService.get_chat_history(
        db=db,
        manager=user,
        chat_id=chat_id,
        limit=limit,
        offset=offset,
    )
