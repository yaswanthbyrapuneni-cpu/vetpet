import asyncio
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from fastapi import WebSocket


class EventHub:
    """Tracks live WebSocket connections per user and pushes JSON events to them."""

    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    def connect(self, user_id: str, socket: WebSocket) -> None:
        self.connections[user_id].append(socket)

    def disconnect(self, user_id: str, socket: WebSocket) -> None:
        sockets = self.connections.get(user_id)
        if not sockets:
            return
        if socket in sockets:
            sockets.remove(socket)
        if not sockets:
            self.connections.pop(user_id, None)

    async def _send(self, user_id: str, socket: WebSocket, event: dict[str, Any]) -> None:
        try:
            await socket.send_json(event)
        except Exception:
            self.disconnect(user_id, socket)

    async def send_to_user(self, user_id: str, event: dict[str, Any]) -> None:
        sockets = list(self.connections.get(user_id, []))
        if not sockets:
            return
        await asyncio.gather(*(self._send(user_id, socket, event) for socket in sockets))

    async def send_to_users(self, user_ids: Iterable[str | None], event: dict[str, Any]) -> None:
        unique_ids = {uid for uid in user_ids if uid}
        if not unique_ids:
            return
        await asyncio.gather(*(self.send_to_user(user_id, event) for user_id in unique_ids))


event_hub = EventHub()
