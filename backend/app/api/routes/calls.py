import json
from collections import defaultdict

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.domain import Appointment, AppointmentStatus, DoctorProfile, Pet, User, UserRole

router = APIRouter(prefix="/calls")


class CallRooms:
    def __init__(self) -> None:
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def join(self, appointment_id: str, socket: WebSocket) -> bool:
        room = self.rooms[appointment_id]
        if len(room) >= 2:
            return False
        room.append(socket)
        if len(room) == 2:
            await room[0].send_json({"type": "peer-ready", "initiator": True})
            await room[1].send_json({"type": "peer-ready", "initiator": False})
        return True

    async def relay(self, appointment_id: str, sender: WebSocket, message: dict) -> None:
        for socket in self.rooms.get(appointment_id, []):
            if socket is not sender:
                await socket.send_json(message)

    async def leave(self, appointment_id: str, socket: WebSocket) -> None:
        room = self.rooms.get(appointment_id, [])
        if socket in room:
            room.remove(socket)
        for peer in room:
            await peer.send_json({"type": "peer-left"})
        if not room:
            self.rooms.pop(appointment_id, None)


rooms = CallRooms()


def can_join_call(appointment_id: str, token: str) -> bool:
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError:
        return False
    with SessionLocal() as db:
        user = db.get(User, user_id)
        appointment = db.get(Appointment, appointment_id)
        if user is None or not user.is_active or appointment is None:
            return False
        if appointment.status != AppointmentStatus.CONFIRMED:
            return False
        if user.role == UserRole.OWNER:
            return db.scalar(select(Pet.id).where(Pet.id == appointment.pet_id, Pet.owner_id == user.id)) is not None
        if user.role == UserRole.DOCTOR:
            return db.scalar(select(DoctorProfile.id).where(DoctorProfile.id == appointment.doctor_id, DoctorProfile.user_id == user.id)) is not None
        return False


@router.websocket("/ws/{appointment_id}")
async def call_signaling(socket: WebSocket, appointment_id: str) -> None:
    await socket.accept()
    try:
        raw = await socket.receive_text()
        auth = json.loads(raw)
        if auth.get("type") != "auth" or not can_join_call(appointment_id, auth.get("token", "")):
            await socket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Call access denied")
            return
        if not await rooms.join(appointment_id, socket):
            await socket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Call room is full")
            return
        await socket.send_json({"type": "authenticated"})
        while True:
            message = await socket.receive_json()
            if message.get("type") in {"offer", "answer", "ice-candidate"}:
                await rooms.relay(appointment_id, socket, message)
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        await rooms.leave(appointment_id, socket)
