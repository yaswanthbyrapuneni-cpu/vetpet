import json
from collections import defaultdict
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.api.dependencies import DbSession, require_roles
from app.api.routes.appointments import (
    doctor_profile_for_user,
    get_doctor_appointment,
    get_owner_appointment,
)
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.domain import Appointment, AppointmentStatus, DoctorProfile, Pet, User, UserRole
from app.services.notifications import notification_user_for_doctor
from app.services.realtime import event_hub

router = APIRouter()
DoctorUser = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]


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


@router.post("/appointments/{appointment_id}/call/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_to_call(appointment_id: str, doctor: DoctorUser, db: DbSession) -> None:
    """The assigned doctor rings the owner: pushes a WhatsApp-style incoming-call event."""
    profile = doctor_profile_for_user(db, doctor.id)
    appointment = get_doctor_appointment(db, appointment_id, profile.id)
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only confirmed appointments can be called")
    owner_user_id = db.scalar(select(Pet.owner_id).where(Pet.id == appointment.pet_id))
    if owner_user_id:
        await event_hub.send_to_user(
            owner_user_id,
            {
                "type": "call_invite",
                "appointment_id": appointment.id,
                "doctor_name": doctor.full_name,
                "consultation_type": appointment.consultation_type,
            },
        )


@router.post("/appointments/{appointment_id}/call/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_call(appointment_id: str, owner: OwnerUser, db: DbSession) -> None:
    """The owner declines an incoming call: tells the doctor so they stop ringing/waiting."""
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    doctor_user_id = notification_user_for_doctor(db, appointment.doctor_id)
    if doctor_user_id:
        await event_hub.send_to_user(
            doctor_user_id, {"type": "call_declined", "appointment_id": appointment.id}
        )


@router.post("/appointments/{appointment_id}/call/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_call(appointment_id: str, doctor: DoctorUser, db: DbSession) -> None:
    """The doctor cancels a call before the owner answers: dismisses their ringing overlay."""
    profile = doctor_profile_for_user(db, doctor.id)
    appointment = get_doctor_appointment(db, appointment_id, profile.id)
    owner_user_id = db.scalar(select(Pet.owner_id).where(Pet.id == appointment.pet_id))
    if owner_user_id:
        await event_hub.send_to_user(
            owner_user_id, {"type": "call_cancelled", "appointment_id": appointment.id}
        )


@router.websocket("/calls/ws/{appointment_id}")
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
