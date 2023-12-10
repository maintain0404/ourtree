from __future__ import annotations

import asyncio as aio
import random as rd
from datetime import datetime
from uuid import uuid4

import reflex as rx

from server.services.channel import (
    BaseUserConnection,
    Channel,
    ChannelController,
    Event,
    Object,
    Position,
    User,
)
from server.templates import template


class RxObject(rx.Base, Object):
    ...


class RxEvent(rx.Base, Event):
    ...


class RxUser(rx.Base, User):
    ...


controller = ChannelController()


class CanvasState(rx.State, BaseUserConnection):
    objects: list[RxObject]
    events: list[Event]
    _channel: Channel
    _user: RxUser | None
    new_object: RxObject | None = None
    last_apppended: datetime = datetime(2000, 1, 1, 1, 0, 0)

    async def send(self, event: Event):
        async with self:
            self.events.append(RxEvent(__root__=event.dict()))
            if event.type == "push-object":
                self.objects.append(RxObject(**event.object.dict()))
            elif event.type == "error":
                rx.window_alert("Error!")

    async def recieve(self) -> Event:
        ...

    @rx.background
    async def enter_page(self):
        channel_id = self.router.page.path
        async with self:
            # get channel
            self._channel = controller.get_channel(channel_id)
            if self._channel is None:
                self._channel = controller.create_channel(channel_id)

            # Load already pushed objects
            self.objects = [
                RxObject(**o.dict()) for o in self._channel.objects.values()
            ]

            # Join channel
            self._user = RxUser(
                id=self.router.session.client_token,
                nickname="User",
                session=self.router.session.client_token,
                connection=self,
            )
            await self._channel.join(
                User(
                    id=self._user.id,
                    nickname=self._user.nickname,
                    session=self._user.session,
                    connection=self._user.connection,
                )
            )

        print(self._channel)

    async def push_object(self):
        self.new_object = RxObject(
            id=str(uuid4()),
            url="/github.svg",
            comment="hello",
            created_at=datetime.now(),
            position=Position(x=rd.randint(1, 959), y=rd.randint(1, 1259)),
        )
        await self._channel.push_object(
            Object(**self.new_object.dict()),
            appender=User(
                id=self._user.id,
                nickname=self._user.nickname,
                session=self._user.session,
                connection=self._user.connection,
            ),
        )
        self.objects.append(self.new_object)


def render_object(o: Object):
    return rx.box(
        rx.image(
            src=o.url,
        ),
    )


@template(route="/canvas", title="Canvas", on_load=CanvasState.enter_page)
def canvas():
    return rx.container(
        rx.box(rx.foreach(CanvasState.objects, render_object)),
        rx.button("Go", on_click=CanvasState.push_object),
        bg="green",
        width=1260,
        height=960,
    )
