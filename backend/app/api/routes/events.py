import json

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.domain import User
from app.services.realtime import event_hub

router = APIRouter()


def authenticated_user_id(token: str) -> str | None:
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError:
        return None
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user.id


@router.websocket("/ws/events")
async def stream_events(socket: WebSocket) -> None:
    await socket.accept()
    user_id: str | None = None
    try:
        raw = await socket.receive_text()
        auth = json.loads(raw)
        if auth.get("type") != "auth":
            await socket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required"
            )
            return
        user_id = authenticated_user_id(auth.get("token", ""))
        if user_id is None:
            await socket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired session"
            )
            return
        event_hub.connect(user_id, socket)
        await socket.send_json({"type": "connected"})
        while True:
            await socket.receive_text()
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        if user_id is not None:
            event_hub.disconnect(user_id, socket)
