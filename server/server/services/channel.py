"""Channel."""
from __future__ import annotations

from collections import deque
from asyncio import Lock, TaskGroup, wait_for
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal

import reflex as rx

from server.base import BaseModel, Field


class Position(BaseModel):
    """Posision of objects."""
    x: int
    y: int


class Object(BaseModel):
    """Tree decoration object."""

    id: str
    url: str
    comment: str
    created_at: datetime = Field(default_factory=datetime.now)
    position: Position


class BaseUserConnection:
    async def receive(self) -> Event:
        ...

    async def send(self, data: Event):
        ...


class UserInfo(BaseModel):
    id: str
    nickname: str


class User(UserInfo):
    """User."""

    session: str
    connection: BaseUserConnection

    class Config:
        arbitrary_types_allowed = True


class BaseEvent(BaseModel):
    """Event base classs"""

    type: str


    def as_message(self) -> str:
        ...


class JoinEvent(BaseEvent):
    """Event data for user join."""
    type: Literal["join"] = "join"
    user: UserInfo

    def as_message(self) -> str:
        return f'{self.user.nickname} 님이 채널에 참여했어요!'


class PushObjectEvent(BaseEvent):
    """Event data for pushing new object."""
    type: Literal["push-object"] = "push-object"
    object: Object
    appender: UserInfo
    pop: str | None

    def as_message(self) -> str:
        return f'{self.appender.nickname} 님이 새로 트리를 장식했어요!'


class LeaveEvent(BaseEvent):
    """Event data for user leaving."""
    type: Literal["leave"] = "leave"
    user: UserInfo

    def as_message(self) -> str:
        return f'{self.user.nickname} 님이 채널을 나갔어요!'



class ErrorEvent(BaseEvent):
    """Event data for error."""
    type: Literal["error"] = "error"
    code: str
    message: str

    def as_message(self) -> str:
        return f'알 수 없는 오류가 발생헀어요.(code: {self.code}, message: {self.message})'


class Event(BaseModel):
    """Event data."""
    __root__: Annotated[
        JoinEvent | PushObjectEvent | LeaveEvent | ErrorEvent,
        Field(discriminator="type"),
    ]


class Channel(BaseModel):
    """Represent group tree channel."""

    id: str
    users: dict[str, User] = Field(default_factory=dict)
    # events: deque[str] = Field(default_factory=lambda: deque(maxlen=30))
    objects: dict[str, Object] = Field(default_factory=dict)
    channel_controller: ChannelController | None = Field(None, exclude=True, repr=False)
    policy: ChannelPolicy | None = None

    event_lock: Lock = Field(Lock(), const=True)

    class Config:
        arbitrary_types_allowed = True

    def get_event_lock(self, publisher: User | None):
        @asynccontextmanager
        async def inner():
            try:
                await wait_for(self.event_lock.acquire(), timeout=self.policy.timeout)
                yield True
            except TimeoutError:
                if publisher:
                    await publisher.connection.send(
                        ErrorEvent(code="timeout", message="Timeout")
                    )
                yield False
            finally:
                if self.event_lock.locked():
                    self.event_lock.release()
  

        return inner()

    def initialize(self, channel_controller: ChannelController, policy: ChannelPolicy):
        assert self.channel_controller is None
        assert self.policy is None
        self.channel_controller = channel_controller
        self.policy = policy

    async def _publish_event(self, event: Event, publisher_id: str | None):
        try:
            async with TaskGroup() as tg:
                for user in self.users.values():
                    if user.id != publisher_id:
                        tg.create_task(user.connection.send(event))
        except ExceptionGroup:
            await self.users[publisher_id].connection.send(
                ErrorEvent(code="unknown", message="Failed with unknown reason")
            )

    async def join(self, user: User) -> None:
        async with self.get_event_lock(user) as can_go:
            if not can_go:
                return

            if user.id in self.users.keys():
                return

            if len(self.users) >= self.policy.max_ccu:
                await user.connection.send(
                    ErrorEvent(code="full", message="Full users")
                )
            else:
                self.users[user.id] = user
                await self._publish_event(JoinEvent(user=user), user.id)

    async def push_object(self, obj: Object, appender: User):
        async with self.get_event_lock(appender) as can_go:
            if not can_go:
                return

            if appender.id not in self.users.keys():
                await appender.connection.send(
                    ErrorEvent(code="invalid", message="invalid")
                )

            if len(self.objects) >= self.policy.max_objects:
                firstkey, _ = next(iter(self.objects.items()))
                del self.objects[firstkey]
            else:
                firstkey = None
            self.objects[obj.id] = obj
            await self._publish_event(
                PushObjectEvent(appender=appender, object=obj, pop=firstkey),
                appender.id,
            )

    async def leave(self, user: User):
        # This method is executed when disconnected.
        # If leave event must be pulbished.
        self.users.pop(user.id, None)
        if len(self.users) > 0:
            await self._publish_event(LeaveEvent(user=user), user.id)
        else:
            self.channel_controller.close_channel(self.id)


class ChannelPolicy(BaseModel):
    max_objects: int = 30
    max_ccu: int = 10
    timeout: float | int = 1
    cooltime: int = 10


class ChannelController(BaseModel):
    channels: dict[str, Channel] = Field(default_factory=dict)

    def get_channel(self, channel_id: str) -> Channel | None:
        return self.channels.get(channel_id, None)

    def create_channel(self, channel_id: str) -> Channel | None:
        if channel_id in self.channels:
            return self.channels.get(channel_id)
        else:
            channel = Channel(id=channel_id)
            self.channels[channel_id] = channel
            # TODO: Remove policy hard coding
            channel.initialize(self, ChannelPolicy(max_objects=30, max_ccu=10))
            return channel

    def close_channel(self, channel_id: str) -> None:
        assert channel_id in self.channels
        del self.channels[channel_id]
