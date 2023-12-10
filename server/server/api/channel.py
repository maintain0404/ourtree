"""Channel API."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/channel")


class WebsocketConnection:
    ws: WebSocket

    async def handshake(self):
        await self.ws.accept()

        await self.ws.receive_json()

        await self.ws.send_json()

    async def receive(self, event):
        ...

    async def send(self, event):
        ...


@router.get("/@{channel_name}")
async def channel_api(channel_name: str, ws: WebSocket):
    ...
