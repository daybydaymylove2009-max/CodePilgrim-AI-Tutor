from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

from app.algorithms.ercf import ERCFContext, PersonaStage
from app.core.deps import get_current_user
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.services.ai_tutor import ai_tutor_service

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.session_contexts: dict[str, ERCFContext] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.session_contexts[user_id] = ERCFContext(persona=PersonaStage.GUIDE)
        logger.info(f"WebSocket connected: user={user_id}")

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        self.session_contexts.pop(user_id, None)
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_message(self, user_id: str, message: dict):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/tutor/{token}")
async def websocket_tutor(websocket: WebSocket, token: str):
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            kp_id = message_data.get("kp_id")
            kp_title = message_data.get("kp_title", "")
            user_message = message_data.get("message", "")
            p_know = message_data.get("p_know", 0.2)

            if not kp_id or not user_message:
                await manager.send_message(user_id, {
                    "type": "error",
                    "message": "kp_id and message are required",
                })
                continue

            ctx = manager.session_contexts.get(user_id, ERCFContext())

            await manager.send_message(user_id, {
                "type": "typing",
                "ercf_stage": ctx.stage.value,
                "persona_stage": ctx.persona.value,
            })

            try:
                response = await ai_tutor_service.chat(
                    message=user_message,
                    kp_id=uuid.UUID(kp_id),
                    kp_title=kp_title,
                    p_know=p_know,
                    context=ctx,
                )

                manager.session_contexts[user_id] = ctx

                await manager.send_message(user_id, {
                    "type": "message",
                    "assistant_message": response["assistant_message"],
                    "ercf_stage": response["ercf_stage"],
                    "persona_stage": response["persona_stage"],
                    "hint_level": response.get("hint_level"),
                    "intervention": response.get("intervention"),
                })

            except Exception as e:
                logger.error(f"AI tutor error for user={user_id}: {e}")
                await manager.send_message(user_id, {
                    "type": "error",
                    "message": "AI tutor encountered an error, please try again",
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user={user_id}: {e}")
        manager.disconnect(user_id)
